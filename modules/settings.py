from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFormLayout, QLineEdit, QComboBox,
                             QMessageBox, QFileDialog, QGroupBox, QCheckBox, QFrame,
                             QDialog, QScrollArea, QGridLayout)
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import Qt, QSettings, QThread, pyqtSignal
from core.backup import BackupManager
from utils.paths import get_app_path
from core.logger import logger
from core.version import VERSION
import hashlib
import os
import binascii
class RestoreWorker(QThread):
    success = pyqtSignal()
    error = pyqtSignal(str)
    def __init__(self, backup_manager, file_path, parent=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.file_path = file_path
    def run(self):
        try:
            result = self.backup_manager.restore_backup(self.file_path)
            if result:
                self.success.emit()
            else:
                self.error.emit("恢复未成功")
        except Exception as e:
            self.error.emit(str(e))

class ChangeUsernameDialog(QDialog):
    """修改用户名对话框"""
    def __init__(self, auth_manager, current_user, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.current_user = current_user
        self.setWindowTitle('修改用户名')
        self.setFixedSize(400, 200)
        self._init_ui()
        
    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入当前密码以验证身份")
        layout.addRow("当前密码:", self.password_input)
        
        self.new_username_input = QLineEdit()
        self.new_username_input.setPlaceholderText("请输入新用户名")
        layout.addRow("新用户名:", self.new_username_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow("", btn_layout)
        
    def _save(self):
        password = self.password_input.text()
        new_username = self.new_username_input.text().strip()
        
        if not password or not new_username:
            QMessageBox.warning(self, "警告", "请填写完整信息")
            return
            
        success, msg = self.auth_manager.change_username(self.current_user, password, new_username)
        if success:
            QMessageBox.information(self, "成功", "用户名修改成功，请重新登录")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", f"修改失败: {msg}")

class SettingsWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_manager = main_window.app.db_manager
        self.backup_manager = main_window.app.backup_manager
        self.settings = QSettings("CustomerManagement", "Settings")
        self._init_ui()
        self._load_saved_settings()
        
    def _load_saved_settings(self):
        """加载保存的设置"""
        # 加载主题设置
        saved_theme = self.settings.value("theme", "浅色", type=str)
        index = self.theme_combo.findText(saved_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        # 加载关闭行为设置
        close_to_tray = self.settings.value("close_to_tray", False, type=bool)
        dont_ask_close = self.settings.value("dont_ask_close", False, type=bool)
        self.close_to_tray_check.setChecked(close_to_tray)
        self.dont_ask_close_check.setChecked(dont_ask_close)
            
        # 加载自动备份设置
        auto_backup = self.settings.value("auto_backup", True, type=bool)
        self.auto_backup_check.setChecked(auto_backup)
        
        # 加载备份路径
        backup_path = self.settings.value("backup_path", "", type=str)
        if not backup_path:
            backup_path = get_app_path('backups')
        self.backup_path_input.setText(backup_path)
        
    def _init_ui(self):
        """初始化设置界面"""
        # 主布局（包含滚动区域和底部按钮）
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        main_layout.addWidget(scroll)
        
        # 内容容器
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        # 内容布局
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # 创建网格布局用于左右分栏
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        content_layout.addLayout(grid_layout)

        # 左侧列容器
        left_column = QVBoxLayout()
        left_column.setSpacing(20)
        
        # 右侧列容器
        right_column = QVBoxLayout()
        right_column.setSpacing(20)

        # 将左右列添加到网格
        grid_layout.addLayout(left_column, 0, 0)
        grid_layout.addLayout(right_column, 0, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        
        # --- 系统设置卡片 (左侧) ---
        system_card = QFrame()
        system_card.setProperty("class", "card")
        system_layout = QVBoxLayout(system_card)
        
        system_title = QLabel('系统设置')
        system_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        system_layout.addWidget(system_title)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # 主题选择
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['浅色', '深色', '系统默认'])
        form_layout.addRow('界面主题:', self.theme_combo)
        
        # 关闭行为设置 (使用分组框优化显示)
        close_group = QGroupBox("关闭设置")
        close_layout = QVBoxLayout(close_group)
        close_layout.setSpacing(10)
        
        self.close_to_tray_check = QCheckBox('关闭时缩小到系统托盘')
        self.dont_ask_close_check = QCheckBox('关闭时不再询问')
        
        close_layout.addWidget(self.close_to_tray_check)
        close_layout.addWidget(self.dont_ask_close_check)
        
        # 添加提示说明
        tip_label = QLabel("提示：若勾选“不再询问”，系统将默认执行当前选择的操作（缩小到托盘或直接退出）。")
        tip_label.setStyleSheet("color: #666; font-size: 12px; margin-top: 5px;")
        tip_label.setWordWrap(True)
        close_layout.addWidget(tip_label)
        
        form_layout.addRow(close_group)
        
        system_layout.addLayout(form_layout)
        left_column.addWidget(system_card)

        # --- 用户管理卡片 (左侧) ---
        user_card = QFrame()
        user_card.setProperty("class", "card")
        user_layout = QVBoxLayout(user_card)
        
        user_title = QLabel('用户管理')
        user_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        user_layout.addWidget(user_title)
        
        user_form = QFormLayout()
        user_form.setSpacing(15)
        
        # 当前用户
        current_user_text = f"{self.main_window.current_user} (管理员)" if self.main_window.current_user else self.main_window.app.auth_manager.settings.value('remember_username', 'admin')
        self.current_user_label = QLabel(current_user_text)
        user_form.addRow('当前用户:', self.current_user_label)
        
        # 密码修改
        change_pwd_btn = QPushButton('修改密码')
        change_pwd_btn.setProperty("class", "info")
        change_pwd_btn.setFixedWidth(120)
        change_pwd_btn.clicked.connect(self._change_password)
        
        # 用户名修改
        change_user_btn = QPushButton('修改用户名')
        change_user_btn.setProperty("class", "warning")
        change_user_btn.setFixedWidth(120)
        change_user_btn.clicked.connect(self._change_username)
        
        btn_container = QHBoxLayout()
        btn_container.addWidget(change_pwd_btn)
        btn_container.addWidget(change_user_btn)
        btn_container.addStretch()
        
        user_form.addRow('', btn_container)
        
        user_layout.addLayout(user_form)
        left_column.addWidget(user_card)

        # --- 关于系统卡片 (左侧) ---
        about_card = QFrame()
        about_card.setProperty("class", "card")
        about_layout = QVBoxLayout(about_card)
        
        about_title = QLabel('关于系统')
        about_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        about_layout.addWidget(about_title)
        
        version_label = QLabel(f"当前版本: {VERSION}")
        version_label.setStyleSheet("font-size: 14px; color: #606266;")
        about_layout.addWidget(version_label)
        
        left_column.addWidget(about_card)
        
        # --- 数据库工具卡片 (右侧) ---
        db_card = QFrame()
        db_card.setProperty("class", "card")
        db_layout = QVBoxLayout(db_card)
        
        db_title = QLabel('数据库工具')
        db_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        db_layout.addWidget(db_title)
        
        usage_group = QGroupBox("使用说明")
        usage_layout = QVBoxLayout(usage_group)
        usage_label = QLabel(
            "自动备份：启用后，系统在每次关闭时自动备份到“备份位置”。\n"
            "手动备份：点击“立即备份数据库”，将当前数据打包到“备份位置”。\n"
            "从备份恢复（两种方式）：\n"
            "  1）在本页面点击“从备份恢复”，选择备份ZIP，恢复完成后程序会自动退出，请重新启动。\n"
            "  2）手动解压备份文件（如：backup_20260127_162851.zip），将其中的\n"
            "     app_data.db、app_data.db-wal、app_data.db-shm（三个核心文件）覆盖到 data 目录；\n"
            "     若压缩包包含 business.db，可一并覆盖。随后重新启动程序。"
        )
        usage_label.setWordWrap(True)
        usage_layout.addWidget(usage_label)
        db_layout.addWidget(usage_group)
        
        # 自动备份设置
        backup_group = QGroupBox("自动备份配置")
        backup_layout = QVBoxLayout(backup_group)
        
        self.auto_backup_check = QCheckBox('启用关闭系统时自动保存数据库')
        backup_layout.addWidget(self.auto_backup_check)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("备份位置:"))
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setReadOnly(True)
        path_layout.addWidget(self.backup_path_input)
        
        select_path_btn = QPushButton("更改位置")
        select_path_btn.clicked.connect(self._select_backup_path)
        path_layout.addWidget(select_path_btn)
        
        backup_layout.addLayout(path_layout)
        db_layout.addWidget(backup_group)
        
        # 手动操作区域
        manual_group = QGroupBox("手动操作")
        manual_layout = QHBoxLayout(manual_group)
        
        # 备份按钮
        backup_btn = QPushButton('立即备份数据库')
        backup_btn.setProperty("class", "primary")
        backup_btn.clicked.connect(self._backup_database)
        manual_layout.addWidget(backup_btn)
        
        # 恢复按钮
        restore_btn = QPushButton('从备份恢复')
        restore_btn.setProperty("class", "warning")
        restore_btn.clicked.connect(self._restore_database)
        manual_layout.addWidget(restore_btn)
        
        db_layout.addWidget(manual_group)
        right_column.addWidget(db_card)
        
        # 左右列底部填充，确保顶部对齐
        left_column.addStretch()
        right_column.addStretch()

        
        # 底部按钮栏（固定在底部）
        bottom_bar = QFrame()
        bottom_bar.setObjectName("settings-bottom-bar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        bottom_layout.addStretch()
        
        save_btn = QPushButton('保存设置')
        # 直接设置样式表以确保生效
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #67c23a;
                border: 1px solid #67c23a;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #85ce61;
                border-color: #85ce61;
            }
            QPushButton:pressed {
                background-color: #5daf34;
                border-color: #5daf34;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        bottom_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(lambda: self.main_window.switch_to_dashboard())
        bottom_layout.addWidget(cancel_btn)
        
        main_layout.addWidget(bottom_bar)
        
    def _select_backup_path(self):
        """选择备份路径"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择备份保存位置",
            self.backup_path_input.text()
        )
        if directory:
            self.backup_path_input.setText(directory)

    def _backup_database(self):
        """手动备份数据库"""
        try:
            # 获取当前设置的备份路径
            custom_path = self.backup_path_input.text().strip()
            
            # 如果路径为空，使用默认路径
            if not custom_path:
                custom_path = None
                
            backup_path = self.backup_manager.create_backup(backup_dir=custom_path)
            
            QMessageBox.information(
                self, 
                '备份成功', 
                f'数据库已成功备份到:\n{backup_path}'
            )
        except Exception as e:
            QMessageBox.critical(
                self, 
                '备份失败', 
                f'备份过程中发生错误:\n{str(e)}'
            )
            
    def _restore_database(self):
        """从备份恢复数据库"""
        import sys
        import time
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            '选择备份文件', 
            self.backup_path_input.text(), 
            '备份文件 (*.zip)'
        )
        
        if not file_path:
            return
            
        reply = QMessageBox.question(
            self,
            '确认恢复',
            '恢复操作将覆盖当前数据库，应用程序将需要重启。\n是否继续?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
            
        if self.db_manager:
            self.db_manager.close()
            time.sleep(1)
        progress = QProgressDialog('正在恢复，请稍候...', None, 0, 0, self)
        progress.setWindowTitle('正在恢复')
        progress.setCancelButton(None)
        progress.setWindowModality(Qt.ApplicationModal)
        progress.show()
        def on_success():
            progress.close()
            QMessageBox.information(
                self,
                '恢复成功',
                '数据库已从备份成功恢复。\n应用程序将立即关闭，请手动重新启动以加载新数据。'
            )
            sys.exit(0)
        def on_error(msg):
            progress.close()
            QMessageBox.critical(
                self, 
                '恢复失败', 
                f'恢复过程中发生错误:\n{msg}\n\n由于数据库连接已关闭，应用程序即将退出。'
            )
            sys.exit(1)
        self._restore_worker = RestoreWorker(self.backup_manager, file_path, self)
        self._restore_worker.success.connect(on_success)
        self._restore_worker.error.connect(on_error)
        self._restore_worker.start()
            
    def _change_username(self):
        """修改用户名"""
        current_user = self.main_window.app.auth_manager.settings.value('remember_username', 'admin') # 简单获取当前用户，实际应从session获取
        # 由于我们没有完善的session管理，暂时假设当前登录用户
        # 更准确的做法是在LoginWindow登录成功后保存current_user到MainApplication
        
        # 尝试从mainwindow获取
        if hasattr(self.main_window, 'current_user') and self.main_window.current_user:
            current_user = self.main_window.current_user
        
        dialog = ChangeUsernameDialog(self.main_window.app.auth_manager, current_user, self)
        if dialog.exec_() == QDialog.Accepted:
            # 退出登录
            self.main_window.logout()

    def _change_password(self):
        """修改当前用户密码"""
        dialog = QDialog(self)
        dialog.setWindowTitle('修改密码')
        dialog.setFixedSize(400, 250)
        
        form_layout = QFormLayout()
        
        current_pwd = QLineEdit()
        current_pwd.setPlaceholderText('输入当前密码')
        current_pwd.setEchoMode(QLineEdit.Password)
        form_layout.addRow('当前密码:', current_pwd)
        
        new_pwd = QLineEdit()
        new_pwd.setPlaceholderText('输入新密码')
        new_pwd.setEchoMode(QLineEdit.Password)
        form_layout.addRow('新密码:', new_pwd)
        
        confirm_pwd = QLineEdit()
        confirm_pwd.setPlaceholderText('确认新密码')
        confirm_pwd.setEchoMode(QLineEdit.Password)
        form_layout.addRow('确认密码:', confirm_pwd)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.clicked.connect(lambda: self._save_password(
            dialog, current_pwd.text(), new_pwd.text(), confirm_pwd.text()
        ))
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addRow(btn_layout)
        
        dialog.setLayout(form_layout)
        dialog.exec_()
        
    def _save_password(self, dialog, current_pwd, new_pwd, confirm_pwd):
        """保存新密码"""
        if not all([current_pwd, new_pwd, confirm_pwd]):
            QMessageBox.warning(dialog, '错误', '请填写所有密码字段')
            return
            
        if new_pwd != confirm_pwd:
            QMessageBox.warning(dialog, '错误', '新密码与确认密码不匹配')
            return
            
        # 验证当前密码
        auth_manager = self.main_window.app.auth_manager
        current_user = self.main_window.current_user
        if not current_user:
            current_user = auth_manager.settings.value('remember_username', 'admin')
            
        success, message = auth_manager.authenticate(current_user, current_pwd)
        
        if not success:
            QMessageBox.warning(dialog, '错误', '当前密码不正确')
            return
            
        # 更新密码
        success, message = auth_manager.update_password(current_user, new_pwd)
        
        if success:
            QMessageBox.information(dialog, '成功', '密码已更新')
            dialog.accept()
        else:
            QMessageBox.critical(dialog, '错误', f'密码更新失败:\n{message}')
            
    def _save_settings(self):
        """保存系统设置"""
        theme = self.theme_combo.currentText()
        auto_backup = self.auto_backup_check.isChecked()
        backup_path = self.backup_path_input.text()
        close_to_tray = self.close_to_tray_check.isChecked()
        dont_ask_close = self.dont_ask_close_check.isChecked()
        
        # 保存到QSettings
        self.settings.setValue("theme", theme)
        self.settings.setValue("auto_backup", auto_backup)
        self.settings.setValue("backup_path", backup_path)
        self.settings.setValue("close_to_tray", close_to_tray)
        self.settings.setValue("dont_ask_close", dont_ask_close)
        self.settings.sync() # 确保立即写入
        
        QMessageBox.information(
            self, 
            '设置已保存', 
            f'系统设置已保存:\n主题: {theme}\n自动备份: {"启用" if auto_backup else "禁用"}'
        )
        
        # 应用主题
        self._apply_theme(theme)
        
        # 切换主题后自动刷新首页数据（特别是图表主题和提醒样式）
        if hasattr(self.main_window, 'dashboard') and self.main_window.dashboard:
            self.main_window.dashboard.update_data()
            logger.info("已自动刷新首页数据以适配新主题")
            
        # 刷新工作安排模块的主题（空状态图标）
        if hasattr(self.main_window, 'work_arrangement') and self.main_window.work_arrangement:
            self.main_window.work_arrangement.update_theme()
            logger.info("已刷新工作安排模块以适配新主题")
        
    def _apply_theme(self, theme):
        """应用选择的主题"""
        app = self.main_window.app
        style_path = ""
        
        if theme == '深色':
            style_path = get_app_path('config/dark_style.qss')
            # 如果没有深色主题文件，尝试使用相对路径或报错
            if not os.path.exists(style_path):
                # 尝试当前工作目录下的 config
                fallback_path = os.path.join(os.getcwd(), 'config', 'dark_style.qss')
                if os.path.exists(fallback_path):
                    style_path = fallback_path
                else:
                    QMessageBox.warning(self, "警告", f"深色主题文件不存在:\n{style_path}\n\n备用路径也不存在:\n{fallback_path}")
                    logger.warning(f"深色主题文件不存在: {style_path}")
                    # 可以在这里动态生成深色样式
                    self._apply_dark_theme_inline(app)
                    return
        elif theme == '浅色':
            style_path = get_app_path('config/style.qss')
        else:
            # 系统默认 - 暂时默认为浅色
            style_path = get_app_path('config/style.qss')
            
        if style_path and os.path.exists(style_path):
            try:
                with open(style_path, 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
            except Exception as e:
                logger.error(f"加载主题失败: {e}")

    def _apply_dark_theme_inline(self, app):
        """应用内联深色主题"""
        dark_qss = """
        /* 深色主题全局设置 */
        * {
            font-family: 'Microsoft YaHei', 'Segoe UI', sans-serif;
            font-size: 14px;
            color: #e0e0e0;
            background-color: #2b2b2b;
        }
        
        /* 主窗口背景 */
        QMainWindow, QDialog, QWidget {
            background-color: #2b2b2b;
        }
        
        /* 卡片样式 */
        QFrame[class~="card"] {
            background-color: #333333;
            border: 1px solid #444444;
            border-radius: 8px;
        }
        
        /* 标签 */
        QLabel {
            color: #e0e0e0;
            background-color: transparent;
        }
        
        /* 输入框 */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #333333;
            border: 1px solid #555555;
            color: #e0e0e0;
            padding: 5px;
            border-radius: 4px;
        }
        
        QLineEdit:focus {
            border-color: #409eff;
        }
        
        /* 表格 */
        QTableWidget {
            background-color: #333333;
            border: 1px solid #444444;
            gridline-color: #555555;
            color: #e0e0e0;
        }
        QHeaderView::section {
            background-color: #444444;
            color: #e0e0e0;
            border: 1px solid #555555;
            padding: 5px;
        }
        
        /* 按钮基础样式 */
        QPushButton {
            background-color: #444444;
            border: 1px solid #555555;
            color: #e0e0e0;
            padding: 8px 16px;
            border-radius: 4px;
        }
        
        QPushButton:hover {
            background-color: #555555;
            border-color: #666666;
        }
        
        QPushButton:pressed {
            background-color: #222222;
        }
        
        /* 特殊按钮 */
        QPushButton[class~="primary"] { background-color: #409eff; border-color: #409eff; color: white; }
        QPushButton[class~="primary"]:hover { background-color: #66b1ff; border-color: #66b1ff; }
        
        QPushButton[class~="danger"] { background-color: #f56c6c; border-color: #f56c6c; color: white; }
        QPushButton[class~="danger"]:hover { background-color: #f78989; border-color: #f78989; }
        
        QPushButton[class~="success"] { background-color: #67c23a; border-color: #67c23a; color: white; }
        QPushButton[class~="success"]:hover { background-color: #85ce61; border-color: #85ce61; }
        
        QPushButton[class~="warning"] { background-color: #e6a23c; border-color: #e6a23c; color: white; }
        QPushButton[class~="warning"]:hover { background-color: #ebb563; border-color: #ebb563; }
        
        /* 滚动条 */
        QScrollBar:vertical {
            border: none;
            background: #2b2b2b;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
        app.setStyleSheet(dark_qss)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = SettingsWindow(None)
    window.show()
    sys.exit(app.exec_())
