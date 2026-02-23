import os
import sqlite3
import hashlib
import binascii
import time
from datetime import datetime, timedelta
from PyQt5.QtCore import QSettings
from utils.paths import get_app_path, get_resource_path
from core.logger import logger

class AuthManager:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else get_app_path('auth.db')
        self.notes_path = get_app_path('notes.json')
        self.todo_path = get_app_path('todo_list.json')
        self.icon_path = get_resource_path(os.path.join('assets', 'icons', '48x48.ico'))
        if not os.path.exists(self.icon_path):
            self.icon_path = get_resource_path(os.path.join('assets', 'icons', '32x32.ico'))
        logger.info(f"数据文件路径: {self.db_path}")
        self.settings = QSettings('MyCompany', 'CustomerSystem')
        self._init_db()
        
    def _init_db(self):
        """初始化认证数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            locked_until TEXT,
            failed_attempts INTEGER DEFAULT 0
        )
        ''')
        
        # 检查是否存在默认用户
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        if user_count == 0:
            # 创建默认用户 admin:admin
            salt = os.urandom(16).hex()
            password_hash = hashlib.pbkdf2_hmac('sha512', 'admin'.encode('utf-8'),
                                              salt.encode('ascii'), 100000)
            password_hash = binascii.hexlify(password_hash).decode('ascii')
            cursor.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                ('admin', password_hash, salt)
            )
            logger.info("已创建默认用户: admin (密码: admin)")
        
        # 创建初始化标记表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_flags (
            flag_name TEXT PRIMARY KEY,
            flag_value TEXT
        )
        ''')
        
        # 检查是否已初始化
        cursor.execute('SELECT flag_value FROM system_flags WHERE flag_name = "initialized"')
        initialized = cursor.fetchone()
        
        # 只在首次运行时创建默认账户
        if not initialized:
            cursor.execute('INSERT INTO system_flags (flag_name, flag_value) VALUES ("initialized", "1")')
        
        conn.commit()
        conn.close()
        
    def _create_user(self, username, password):
        """创建新用户"""
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), 
                                     salt, 100000)
        pwdhash = binascii.hexlify(pwdhash)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)',
            (username, pwdhash.decode('ascii'), salt.decode('ascii'))
        )
        conn.commit()
        conn.close()
        
    def _user_exists(self, username):
        """检查用户是否存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
        
    def update_password(self, username, new_password):
        """更新用户密码"""
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', new_password.encode('utf-8'), 
                                     salt, 100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET password_hash = ?, salt = ? WHERE username = ?',
                (pwdhash, salt.decode('ascii'), username)
            )
            conn.commit()
            conn.close()
            return True, "密码已更新"
        except Exception as e:
            return False, str(e)

    def authenticate(self, username, password, remember_username=False, remember_password=False):
        """验证用户登录"""
        logger.debug(f"正在验证用户: {username}")
        
        # 检查账户是否被锁定
        if self.is_locked(username):
            remaining = self.get_lock_time(username)
            logger.debug(f"账户被锁定，剩余时间: {remaining}秒")
            logger.warning(f"账户已锁定，请{remaining}秒后再试")
            return False, f"账户已锁定，请{remaining}秒后再试"
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT password_hash, salt FROM users WHERE username = ?', 
            (username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            logger.debug(f"用户不存在: {username}")
            logger.warning("用户名或密码错误")
            return False, "用户名或密码错误"
            
        stored_hash, salt = user
        logger.debug(f"存储的哈希: {stored_hash}, 盐值: {salt}")
        
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                     salt.encode('ascii'), 100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        logger.debug(f"计算的哈希: {pwdhash}")
        
        if pwdhash == stored_hash:
            logger.debug("登录成功")
            logger.info("登录成功，重置失败计数")
            self._reset_failed_attempts(username)
            
            # 记住用户名/密码
            if remember_username:
                self.settings.setValue('remember_username', username)
            else:
                self.settings.remove('remember_username')
                
            if remember_password:
                # 注意：实际应用中不应明文存储密码
                self.settings.setValue('remember_password', password)
            else:
                self.settings.remove('remember_password')
                
            return True, "登录成功"
        else:
            # 登录失败，记录失败尝试
            self._record_failed_attempt(username)
            remaining_attempts = 3 - self.get_failed_attempts(username)
            
            if remaining_attempts <= 0:
                self._lock_account(username)
                return False, "账户已锁定30秒"
                
            return False, f"用户名或密码错误，剩余尝试次数: {remaining_attempts}"
    
    def _record_failed_attempt(self, username):
        """记录登录失败尝试"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET failed_attempts = failed_attempts + 1 WHERE username = ?',
            (username,)
        )
        conn.commit()
        conn.close()
        
    def _reset_failed_attempts(self, username):
        """重置登录失败计数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE username = ?',
            (username,)
        )
        conn.commit()
        conn.close()
        
    def _lock_account(self, username):
        """锁定账户30秒"""
        locked_until = datetime.now() + timedelta(seconds=30)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE users SET locked_until = ? WHERE username = ?',
            (locked_until.isoformat(), username)
        )
        conn.commit()
        conn.close()
        
    def is_locked(self, username):
        """检查账户是否被锁定"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT locked_until FROM users WHERE username = ?',
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return False
            
        locked_until = datetime.fromisoformat(result[0])
        return datetime.now() < locked_until
        
    def get_lock_time(self, username):
        """获取剩余锁定时间(秒)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT locked_until FROM users WHERE username = ?',
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return 0
            
        locked_until = datetime.fromisoformat(result[0])
        remaining = (locked_until - datetime.now()).total_seconds()
        return max(0, int(remaining))
        
    def get_failed_attempts(self, username):
        """获取登录失败次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT failed_attempts FROM users WHERE username = ?',
            (username,)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
        
    def get_remembered_credentials(self):
        """获取记住的用户名和密码"""
        username = self.settings.value('remember_username', '')
        password = self.settings.value('remember_password', '')
        return username, password
        
    def change_password(self, username, old_password, new_password):
        """修改用户密码"""
        # 验证旧密码
        success, message = self.authenticate(username, old_password)
        if not success:
            return False, message
            
        # 生成新密码哈希
        salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', new_password.encode('utf-8'), 
                                     salt, 100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        
        # 更新数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE users SET password_hash = ?, salt = ? WHERE username = ?',
                (pwdhash, salt.decode('ascii'), username)
            )
            
            # 如果修改的是默认账户密码，删除默认账户
            if username == 'qjx' and old_password == '654321a':
                cursor.execute('DELETE FROM users WHERE username = ?', ('qjx',))
            
            conn.commit()
            
            # 如果当前记住了密码，更新记住的密码
            if self.settings.value('remember_password'):
                self.settings.setValue('remember_password', new_password)
                
            return True, "密码修改成功"
            
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"数据库错误: {str(e)}"
            
        finally:
            conn.close()

    def change_username(self, old_username, password, new_username):
        """修改用户名"""
        # 验证密码
        success, message = self.authenticate(old_username, password)
        if not success:
            return False, message
            
        # 检查新用户名是否已存在
        if self._user_exists(new_username):
            return False, "该用户名已被使用"
            
        # 检查新用户名是否有效
        if not new_username or len(new_username) < 3:
            return False, "用户名至少需要3个字符"
            
        # 更新数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 更新用户名
            cursor.execute(
                'UPDATE users SET username = ? WHERE username = ?',
                (new_username, old_username)
            )
            
            # 如果修改的是默认账户或旧账户，删除可能残留的旧记录（这里主要处理可能存在的特殊情况）
            # 实际上UPDATE已经处理了，这里只是为了兼容旧代码逻辑
            if old_username == 'qjx' and self._user_exists('qjx'):
                 cursor.execute('DELETE FROM users WHERE username = ?', ('qjx',))
            
            # 更新记住的用户名
            if self.settings.value('remember_username') == old_username:
                self.settings.setValue('remember_username', new_username)
                
            conn.commit()
            return True, "用户名修改成功"
            
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"数据库错误: {str(e)}"
            
        finally:
            conn.close()

if __name__ == '__main__':
    auth = AuthManager()
    # 测试认证功能
    print(auth.authenticate('qjx', '654321a'))
