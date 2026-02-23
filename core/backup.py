import os
import zipfile
import sqlite3
import shutil
from datetime import datetime
import threading
import time
from PyQt5.QtWidgets import QMessageBox
from core.logger import logger

class BackupManager:
    def __init__(self, db_path, backup_dir='backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self._ensure_backup_dir()
        self.timer = None
        
    def _ensure_backup_dir(self):
        """确保备份目录存在"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
    def create_backup(self, backup_dir=None, files=None):
        """创建数据库备份
        Args:
            backup_dir: 备份目录路径，默认为self.backup_dir
            files: 要备份的文件列表，默认为None(备份所有关键文件)
        Returns:
            成功返回备份路径，失败返回None
        """
        try:
            # 确定备份目录
            backup_dir = backup_dir or self.backup_dir
            
            # 确定要备份的文件列表
            if files is None:
                base_dir = os.path.dirname(self.db_path)
                # 定义要备份的数据库文件
                db_files = [
                    os.path.join(base_dir, 'app_data.db'),
                    self.db_path
                ]
                
                # 动态添加相关的 .wal 和 .shm 文件
                files = []
                for db_file in db_files:
                    files.append(db_file)
                    files.append(db_file + '-wal')
                    files.append(db_file + '-shm')
                
                # 去重并确保文件存在
                files = [f for f in dict.fromkeys(files) if os.path.exists(f)]
                
            # 确保备份目录存在并可写
            os.makedirs(backup_dir, exist_ok=True)
            if not os.access(backup_dir, os.W_OK):
                raise PermissionError(f"备份目录不可写: {backup_dir}")
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'backup_{timestamp}.zip')
            
            logger.info(f"[备份] 开始创建备份到: {backup_path}")
            logger.debug(f"[备份] 包含文件: {files}")
            
            # 创建zip备份文件
            with zipfile.ZipFile(backup_path, 'w') as zipf:
                for file in files:
                    if os.path.exists(file):
                        zipf.write(file, os.path.basename(file))
                        logger.debug(f"[备份] 已添加文件: {os.path.basename(file)}")
                    else:
                        logger.warning(f"[备份] 警告: 文件不存在: {file}")
                
            # 验证备份文件
            if not os.path.exists(backup_path):
                raise RuntimeError("备份文件创建失败")
                
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            logger.info(f"[备份] 备份成功创建: {backup_path} (大小: {size_mb:.2f} MB)")
            
            # 自动清理旧备份
            self.clean_old_backups(days=7, backup_dir=backup_dir)
            
            return backup_path
            
        except Exception as e:
            error_msg = f"备份失败: {type(e).__name__} - {str(e)}"
            logger.error(f"[备份] {error_msg}")
            logger.error(f"[备份] 数据库路径: {self.db_path}")
            logger.error(f"[备份] 备份目录: {self.backup_dir}")
            raise Exception(error_msg)

    def clean_old_backups(self, days=7, backup_dir=None):
        """清理超过指定天数的旧备份文件
        Args:
            days: 保留天数
            backup_dir: 备份目录，默认为self.backup_dir
        """
        try:
            target_dir = backup_dir or self.backup_dir
            now = datetime.now()
            count = 0
            
            if not os.path.exists(target_dir):
                return
            
            for filename in os.listdir(target_dir):
                if not filename.startswith('backup_') or not filename.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(target_dir, filename)
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    delta = now - file_time
                
                    if delta.days > days:
                        os.remove(file_path)
                        count += 1
                        logger.info(f"[清理] 已删除过期备份: {filename} (超过 {days} 天)")
                except Exception as e:
                    logger.warning(f"[清理] 处理文件失败 {filename}: {str(e)}")
            
            if count > 0:
                logger.info(f"[清理] 共清理了 {count} 个过期备份文件")
                
        except Exception as e:
            logger.error(f"[清理] 清理旧备份失败: {str(e)}")

            
    def restore_backup(self, backup_path, target_dir=None, clean_temp=True):
        """从备份恢复数据库
        Args:
            backup_path: 备份文件路径
            target_dir: 恢复目标目录，默认为self.db_path所在目录
            clean_temp: 是否清理临时文件，默认为True
        Returns:
            成功返回True，失败抛出异常
        """
        # 确定目标目录
        if target_dir is None:
            target_dir = os.path.dirname(self.db_path)
            
        logger.info(f"[恢复] 开始从备份恢复: {backup_path} -> {target_dir}")
        
        # 关闭内部连接（如果有）
        if hasattr(self, 'db_connection'):
            try:
                self.db_connection.close()
            except:
                pass
        
        # 强制垃圾回收，确保所有文件句柄释放
        import gc
        gc.collect()

        # 创建临时目录
        temp_dir = os.path.join(target_dir, f'restore_temp_{int(time.time())}')
        
        try:
            # 1. 快速解压
            os.makedirs(temp_dir, exist_ok=True)
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            logger.info(f"[恢复] 已解压到临时目录: {temp_dir}")
            
            # 2. 识别并移动文件
            restored_count = 0
            for filename in os.listdir(temp_dir):
                # 只恢复数据库相关文件
                if filename.endswith(('.db', '.db-wal', '.db-shm')):
                    src = os.path.join(temp_dir, filename)
                    dst = os.path.join(target_dir, filename)
                    
                    # 尝试移动/覆盖
                    max_retries = 20
                    for attempt in range(max_retries):
                        try:
                            # 如果目标文件存在，先尝试重命名备份（比直接删除更安全，且能检测占用）
                            if os.path.exists(dst):
                                try:
                                    os.remove(dst)
                                except PermissionError:
                                    # 如果无法删除，说明被占用
                                    raise PermissionError(f"文件被占用: {filename}")
                            
                            shutil.move(src, dst)
                            logger.info(f"[恢复] 已恢复: {filename}")
                            restored_count += 1
                            break
                        except PermissionError:
                            if attempt < max_retries - 1:
                                time.sleep(0.5) # 延长重试间隔
                                logger.warning(f"[恢复] 文件 {filename} 被占用，重试 {attempt+1}/{max_retries}...")
                                continue
                            else:
                                raise Exception(f"无法写入文件 {filename}，请确保程序已完全关闭。")
                        except Exception as e:
                            raise Exception(f"恢复文件 {filename} 失败: {str(e)}")

            if restored_count == 0:
                raise Exception("备份文件中未找到有效的数据库文件")
                
            return True
            
        except Exception as e:
            logger.error(f"[恢复] 失败: {str(e)}")
            raise
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"[恢复] 清理临时目录失败: {str(e)}")
            
    def schedule_daily_backup(self, window=None, interval_hours=24):
        """安排每日自动备份"""
        def backup_task():
            try:
                backup_path = self.create_backup()
                if window:
                    QMessageBox.information(
                        window, 
                        '自动备份完成', 
                        f'数据库已自动备份到:\n{backup_path}'
                    )
            except Exception as e:
                if window:
                    QMessageBox.warning(
                        window,
                        '自动备份失败',
                        f'自动备份失败:\n{str(e)}'
                    )
            finally:
                # 重新安排下一次备份
                self.timer = threading.Timer(interval_hours * 3600, backup_task)
                self.timer.start()
        
        # 启动第一次备份任务
        self.timer = threading.Timer(interval_hours * 3600, backup_task)
        self.timer.start()
        
    def stop_scheduled_backup(self):
        """停止定时备份"""
        if self.timer:
            self.timer.cancel()
            self.timer = None
