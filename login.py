from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, 
                             QCheckBox, QVBoxLayout, QMessageBox, QDialog,
                             QHBoxLayout, QGridLayout, QFrame, QGraphicsDropShadowEffect,
                             QProgressBar)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPixmap
import os
from core.auth import AuthManager
from core.version import VERSION

class ChangeUsernameDialog(QDialog):
    """修改用户名对话框"""
    def __init__(self, auth_manager, username, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.old_username = username
        self.setWindowTitle('修改用户名')
        self.setFixedSize(350, 200)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # 当前密码
        self.current_pwd_label = QLabel('当前密码:')
        self.current_pwd_input = QLineEdit()
        self.current_pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.current_pwd_label)
        layout.addWidget(self.current_pwd_input)
        
        # 新用户名
        self.new_username_label = QLabel('新用户名:')
        self.new_username_input = QLineEdit()
        layout.addWidget(self.new_username_label)
        layout.addWidget(self.new_username_input)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        self.confirm_btn = QPushButton('确认修改')
        self.confirm_btn.clicked.connect(self._handle_change)
        btn_layout.addWidget(self.confirm_btn)
        
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def _handle_change(self):
        """处理用户名修改"""
        current_pwd = self.current_pwd_input.text()
        new_username = self.new_username_input.text().strip()
        
        if not all([current_pwd, new_username]):
            QMessageBox.warning(self, '错误', '请填写所有字段')
            return
            
        success, message = self.auth_manager.change_username(
            self.old_username, current_pwd, new_username
        )
        
        if success:
            QMessageBox.information(self, '成功', '用户名修改成功')
            self.accept()
        else:
            QMessageBox.warning(self, '错误', message)

class ChangePasswordDialog(QDialog):
    """修改密码对话框"""
    def __init__(self, auth_manager, username, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.username = username
        self.setWindowTitle('修改密码')
        self.setFixedSize(350, 250)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # 当前密码
        self.current_pwd_label = QLabel('当前密码:')
        self.current_pwd_input = QLineEdit()
        self.current_pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.current_pwd_label)
        layout.addWidget(self.current_pwd_input)
        
        # 新密码
        self.new_pwd_label = QLabel('新密码:')
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_pwd_label)
        layout.addWidget(self.new_pwd_input)
        
        # 确认新密码
        self.confirm_pwd_label = QLabel('确认新密码:')
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_pwd_label)
        layout.addWidget(self.confirm_pwd_input)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        self.confirm_btn = QPushButton('确认修改')
        self.confirm_btn.clicked.connect(self._handle_change)
        btn_layout.addWidget(self.confirm_btn)
        
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
    def _handle_change(self):
        """处理密码修改"""
        current_pwd = self.current_pwd_input.text()
        new_pwd = self.new_pwd_input.text()
        confirm_pwd = self.confirm_pwd_input.text()
        
        if not all([current_pwd, new_pwd, confirm_pwd]):
            QMessageBox.warning(self, '错误', '请填写所有字段')
            return
            
        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, '错误', '两次输入的新密码不一致')
            return
            
        success, message = self.auth_manager.change_password(
            self.username, current_pwd, new_pwd
        )
        
        if success:
            QMessageBox.information(self, '成功', '密码修改成功')
            self.accept()
        else:
            QMessageBox.warning(self, '错误', message)

class LoginWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.auth_manager = app.auth_manager
        self.setWindowTitle('登录 - 客户资料管理系统')
        self.setFixedSize(500, 400)  # 加大窗口尺寸以适应内容
        self.setAttribute(Qt.WA_TranslucentBackground) # 设置背景透明
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框窗口
        
        self._init_ui()
        
        # 检查记住的凭证
        self._check_remembered_credentials()
        
    def _init_ui(self):
        """初始化UI界面"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)
        
        # 背景容器
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("LoginFrame")
        # 样式移至QSS
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 5)
        self.bg_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.bg_frame)
        
        # 内容布局
        layout = QVBoxLayout(self.bg_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部控制栏
        top_bar_widget = QWidget()
        top_bar_widget.setFixedHeight(40)
        top_bar_layout = QHBoxLayout(top_bar_widget)
        top_bar_layout.setContentsMargins(15, 5, 5, 5) # 调整边距，右侧留出空间给关闭按钮
        
        title_icon = QLabel()
        if hasattr(self.auth_manager, 'icon_path') and os.path.exists(self.auth_manager.icon_path):
            pixmap = QPixmap(self.auth_manager.icon_path)
            title_icon.setPixmap(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            title_icon.setText("📊")
            title_icon.setStyleSheet("font-size: 18px;")
        top_bar_layout.addWidget(title_icon)
        
        title_text = QLabel("客户资料管理系统")
        title_text.setObjectName("LoginTitle")
        # 样式移至QSS
        top_bar_layout.addWidget(title_text)
        
        top_bar_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 20px;
                color: #909399;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #f56c6c;
                color: white;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_bar_layout.addWidget(close_btn)
        
        layout.addWidget(top_bar_widget)
        
        # 登录内容区
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 10, 40, 40)
        content_layout.setSpacing(20)
        
        # 欢迎文字
        welcome_label = QLabel("欢迎登录")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #409eff; margin-bottom: 10px;")
        content_layout.addWidget(welcome_label)
        
        # 用户名
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        self.username_input.setFixedHeight(40)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 5px 15px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        content_layout.addWidget(self.username_input)
        
        # 密码
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 5px 15px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #409eff;
            }
        """)
        content_layout.addWidget(self.password_input)
        
        # 选项
        options_layout = QHBoxLayout()
        self.remember_username_check = QCheckBox('记住账号')
        self.remember_password_check = QCheckBox('记住密码')
        options_layout.addWidget(self.remember_username_check)
        options_layout.addWidget(self.remember_password_check)
        content_layout.addLayout(options_layout)
        
        # 登录按钮
        login_btn = QPushButton('登 录')
        login_btn.setFixedHeight(45)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        login_btn.clicked.connect(self._handle_login)
        content_layout.addWidget(login_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #f0f2f5;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #409eff;
                border-radius: 3px;
            }
        """)
        content_layout.addWidget(self.progress_bar)

        # 版本和作者标签
        info_label = QLabel(f"{VERSION}  |  by 梦想家C")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #909399; font-size: 12px; margin-top: 10px;")
        content_layout.addWidget(info_label)
        
        layout.addWidget(content_widget)
        
        main_layout.addWidget(self.bg_frame)
        
        # 窗口拖动支持
        self._drag_pos = None
        
    # 添加鼠标拖动窗口功能
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()
            
    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        self.m_drag = False
        
    def _check_remembered_credentials(self):
        """检查并填充记住的用户名和密码"""
        username, password = self.auth_manager.get_remembered_credentials()
        if username:
            self.username_input.setText(username)
            self.remember_username_check.setChecked(True)
        if password:
            self.password_input.setText(password)
            self.remember_password_check.setChecked(True)
            
    def _handle_change_username(self):
        """处理修改用户名按钮点击"""
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, '错误', '请先输入用户名')
            return
            
        dialog = ChangeUsernameDialog(self.auth_manager, username, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, '成功', '用户名修改成功')
            # 更新输入框中的用户名
            self.username_input.setText(dialog.new_username_input.text().strip())

    def _handle_change_password(self):
        """处理修改密码按钮点击"""
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, '错误', '请先输入用户名')
            return
            
        dialog = ChangePasswordDialog(self.auth_manager, username, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, '成功', '密码修改成功')
            
    def _handle_login(self):
        """处理登录按钮点击"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        remember_username = self.remember_username_check.isChecked()
        remember_password = self.remember_password_check.isChecked()
        
        if not username or not password:
            QMessageBox.warning(self, '错误', '请输入用户名和密码')
            return
            
        # 检查账户是否被锁定
        if self.auth_manager.is_locked(username):
            remaining = self.auth_manager.get_lock_time(username)
            QMessageBox.warning(
                self, 
                '账户锁定', 
                f'账户已锁定，请{remaining}秒后再试'
            )
            return
            
        # 显示进度条并禁用输入
        self.progress_bar.setVisible(True)
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)
        QApplication.processEvents()

        try:
            # 尝试认证
            success, message = self.auth_manager.authenticate(
                username, 
                password, 
                remember_username=remember_username,
                remember_password=remember_password
            )
            
            if success:
                # 登录成功，显示主窗口
                self.app.create_main_window()
                if hasattr(self.app.main_window, 'current_user'):
                    self.app.main_window.current_user = username
                self.app.main_window.show()
                self.close()
            else:
                # 恢复界面状态
                self.progress_bar.setVisible(False)
                self.username_input.setEnabled(True)
                self.password_input.setEnabled(True)
                
                # 登录失败，显示错误信息
                QMessageBox.warning(self, '登录失败', message)
                
                # 更新剩余尝试次数
                remaining_attempts = 3 - self.auth_manager.get_failed_attempts(username)
                if remaining_attempts <= 0:
                    QTimer.singleShot(30000, lambda: 
                        QMessageBox.information(
                            self, 
                            '解锁通知', 
                            '您的账户已解锁，可以重新尝试登录'
                        )
                    )
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            QMessageBox.critical(self, '系统错误', f'登录过程发生异常: {str(e)}')

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    login_window = LoginWindow(app)
    login_window.show()
    sys.exit(app.exec_())
# print('by 梦想家C')