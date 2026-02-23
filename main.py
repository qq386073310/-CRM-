import sys
import os
import warnings
from datetime import datetime
warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QButtonGroup, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QStyle
from PyQt5.QtCore import QFile, QTextStream, Qt, QSettings, QSize
from utils.paths import get_app_path, get_resource_path
from core.auth import AuthManager
from core.database import DatabaseManager
from core.backup import BackupManager
from core.logger import logger, install_exception_hook
from login import LoginWindow
from dialogs.search_result import SearchResultDialog

class MainApplication(QApplication):
    # 添加DPI感知设置
    from ctypes import windll
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    # 启用高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # 强制设置缩放因子，确保在不同分辨率下显示一致
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # 添加以下代码抑制弃用警告
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    """主应用程序类"""
    def __init__(self, sys_argv):
        super(MainApplication, self).__init__(sys_argv)
        # 安装全局异常钩子
        install_exception_hook()
        
        # 设置默认字体
        font = self.font()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(9)
        self.setFont(font)

        # 注册应用退出时的清理函数
        self.aboutToQuit.connect(self._cleanup)
        
        # 初始化认证模块 (登录界面需要)
        try:
            logger.info("正在初始化认证模块...")
            self.auth_manager = AuthManager()
            logger.info("认证模块初始化成功")
        except Exception as e:
            self._show_critical_error("认证模块初始化失败", f"无法初始化认证模块:\n{str(e)}")
            raise
            
        # 加载样式表
        try:
            logger.info("正在加载样式表...")
            self._load_stylesheet()
            logger.info("样式表加载成功")
        except Exception as e:
            logger.error(f"样式表加载失败: {str(e)}")
            # 样式表失败不影响程序运行
            
        # 主窗口延迟创建
        self.main_window = None
            
        # 显示登录窗口
        try:
            logger.info("正在显示登录窗口...")
            self.login_window = LoginWindow(self)
            self.login_window.show()
            screen_geometry = self.primaryScreen().availableGeometry()
            window_geometry = self.login_window.frameGeometry()
            self.login_window.move(
                (screen_geometry.width() - window_geometry.width()) // 2,
                (screen_geometry.height() - window_geometry.height()) // 2
            )
            logger.info("登录窗口显示成功")
        except Exception as e:
            self._show_critical_error("登录窗口显示失败", f"无法显示登录窗口:\n{str(e)}")
            raise
            
    def create_main_window(self):
        """延迟创建主窗口"""
        if self.main_window is None:
            try:
                # 初始化核心模块（延迟加载）
                if not hasattr(self, 'db_manager'):
                    logger.info("正在初始化数据库...")
                    self.db_manager = DatabaseManager(get_app_path('data/app_data.db'))
                    logger.info(f"数据库初始化成功，路径: {self.db_manager.db_path}")

                if not hasattr(self, 'backup_manager'):
                    self.backup_manager = BackupManager(get_app_path('data/business.db'))

                logger.info("正在创建主窗口...")
                self.main_window = MainWindow(self)
                self.main_window.move(50, 50)
                
                # 强制设置应用图标
                from PyQt5.QtGui import QIcon
                if hasattr(self.auth_manager, 'icon_path') and os.path.exists(self.auth_manager.icon_path):
                    self.setWindowIcon(QIcon(self.auth_manager.icon_path))
                    
                logger.info("主窗口创建成功")
            except Exception as e:
                self._show_critical_error("主窗口创建失败", f"无法创建主窗口:\n{str(e)}")
                raise

    def _show_critical_error(self, title, message):
        """显示错误对话框"""
        logger.critical(f"{title}: {message}")
        from PyQt5.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
        
    def _cleanup(self):
        """应用退出时的清理工作"""
        # 1. 关闭数据库连接
        if hasattr(self, 'db_manager') and self.db_manager:
            logger.info("正在关闭数据库连接...")
            self.db_manager.close()
            logger.info("数据库连接已关闭")
            
        # 2. 执行自动备份
        try:
            # 读取设置
            settings = QSettings("CustomerManagement", "Settings")
            auto_backup = settings.value("auto_backup", True, type=bool)
            
            if auto_backup and hasattr(self, 'backup_manager'):
                logger.info("正在执行退出自动备份...")
                # 获取备份路径
                backup_path = settings.value("backup_path", "", type=str)
                # 执行备份
                result = self.backup_manager.create_backup(backup_path)
                if result:
                    logger.info(f"退出自动备份成功: {result}")
                    
        except Exception as e:
            logger.error(f"退出自动备份失败: {str(e)}")
            
    def _load_stylesheet(self):
        """加载QSS样式表"""
        # 读取保存的主题设置
        settings = QSettings("CustomerManagement", "Settings")
        theme = settings.value("theme", "浅色", type=str)
        
        style_filename = "style.qss" # 默认浅色
        if theme == "深色":
            style_filename = "dark_style.qss"
            
        style_path = get_resource_path(f"config/{style_filename}")
            
        logger.info(f"正在加载主题: {theme}, 路径: {style_path}")
        
        # 检查文件是否存在
        if not os.path.exists(style_path):
            logger.warning(f"样式文件不存在: {style_path}，尝试回退到默认样式")
            if theme == "深色": # 如果深色不存在，回退到浅色
                 style_path = get_resource_path("config/style.qss")
        
        style_file = QFile(style_path)
        if style_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(style_file)
            # 设置编码为UTF-8，防止中文乱码
            stream.setCodec("UTF-8")
            self.setStyleSheet(stream.readAll())
            style_file.close()
            logger.info("样式表加载成功")
        else:
            logger.error(f"样式表加载失败: {style_file.errorString()}")

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QPushButton, QButtonGroup, QSpacerItem, QSizePolicy,
    QStackedWidget, QAction, QSystemTrayIcon, QMenu, QMessageBox, QCheckBox, QDialog, QStyle
)
from PyQt5.QtCore import Qt, QCoreApplication, QSettings

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self, app):
        super(MainWindow, self).__init__()
        self.app = app
        self.setWindowTitle('客户资料管理系统')
        
        # 当前登录用户
        self.current_user = None
        
        # 加载设置
        self.settings = QSettings("CustomerManagement", "Settings") # Use unified settings file name
        
        # 恢复窗口位置和大小
        self.window_settings = QSettings("CustomerManagement", "MainWindow")
        geometry = self.window_settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 智能计算初始窗口大小
            screen = QApplication.primaryScreen().availableGeometry()
            # 默认设置为屏幕的 75% 大小，但不超过 1440x900
            target_width = min(int(screen.width() * 0.75), 1440)
            target_height = min(int(screen.height() * 0.75), 900)
            
            # 确保不小于最小值，但也要适应小屏幕
            # 如果屏幕较小（如平板），则不强制使用大尺寸
            min_w = min(960, int(screen.width() * 0.85))
            min_h = min(600, int(screen.height() * 0.85))
            
            target_width = max(target_width, min_w)
            target_height = max(target_height, min_h)
            
            # 居中显示
            x = (screen.width() - target_width) // 2
            y = (screen.height() - target_height) // 2
            
            self.setGeometry(x, y, target_width, target_height)
            
        # 调小最小尺寸，适配小屏笔记本和平板
        self.setMinimumSize(800, 500)
        
        # 初始化系统托盘
        self._init_tray_icon()
        
        # 创建主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 (水平布局: 侧边栏 + 内容区)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建侧边栏
        self._create_sidebar()
        
        # 创建内容区 (堆叠窗口)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("content-area")
        self.main_layout.addWidget(self.stacked_widget)
        
        # 初始化模块窗口
        from modules.dashboard import DashboardWindow
        
        self.dashboard = DashboardWindow(self)
        self.customer = None
        self.business = None
        self.finance = None
        self.contract = None
        self.work_arrangement = None
        self.invoice_system = None
        self.web_nav = None
        self.settings_window = None
        self.todo_window = None
        self.notes_window = None
        
        # 添加窗口到堆叠
        self.stacked_widget.addWidget(self.dashboard)
        
        # 默认显示首页
        self.btn_dashboard.setChecked(True)
        self.switch_to_dashboard()


    def _create_sidebar(self):
        """创建侧边栏"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # 应用标题
        title_label = QLabel("客户资料管理系统")
        title_label.setObjectName("app-title")
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)
        
        # 导航按钮组
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        # 创建按钮
        self.btn_dashboard = self._add_sidebar_btn("首页", self.switch_to_dashboard, sidebar_layout, QStyle.SP_DesktopIcon)
        self.btn_customer = self._add_sidebar_btn("客户管理", self.switch_to_customer, sidebar_layout, QStyle.SP_DirHomeIcon)
        self.btn_business = self._add_sidebar_btn("业务管理", self.switch_to_business, sidebar_layout, QStyle.SP_DirClosedIcon)
        self.btn_finance = self._add_sidebar_btn("财务记录", self.switch_to_finance, sidebar_layout, QStyle.SP_FileDialogDetailedView)
        self.btn_contract = self._add_sidebar_btn("合同管理", self.switch_to_contract, sidebar_layout, QStyle.SP_FileIcon)
        self.btn_work = self._add_sidebar_btn("工作安排", self.switch_to_work_arrangement, sidebar_layout, QStyle.SP_FileDialogListView)
        self.btn_invoice = self._add_sidebar_btn("发票合并", self.switch_to_invoice, sidebar_layout, "resources/icons/pdf.svg")
        self.btn_web_nav = self._add_sidebar_btn("网站导航", self.switch_to_web_nav, sidebar_layout, QStyle.SP_DriveNetIcon)
        
        # 弹簧撑开底部
        sidebar_layout.addStretch()
        
        # 全局搜索按钮
        self.btn_search = self._add_sidebar_btn("全局搜索", self.open_search_dialog, sidebar_layout, QStyle.SP_FileDialogInfoView)
        
        # 回收站按钮
        self.btn_recycle = self._add_sidebar_btn("回收站", self.open_recycle_bin, sidebar_layout, QStyle.SP_TrashIcon)
        
        # 底部功能按钮
        self.btn_settings = self._add_sidebar_btn("系统设置", self.switch_to_settings, sidebar_layout, QStyle.SP_ComputerIcon)
        
        self.main_layout.addWidget(sidebar)

    def _add_sidebar_btn(self, text, callback, layout, icon_type=None):
        """添加侧边栏按钮"""
        btn = QPushButton(text)
        # 设置属性以便QSS选择器使用
        btn.setProperty("class", "sidebar-btn")
        
        if icon_type:
            if isinstance(icon_type, str):
                from PyQt5.QtGui import QIcon
                icon_path = get_resource_path(icon_type)
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                else:
                    logger.warning(f"Icon not found: {icon_path}")
            else:
                btn.setIcon(self.style().standardIcon(icon_type))
            btn.setIconSize(QSize(20, 20))
            
        # 也可以直接设置类名，配合style.qss中的QPushButton[class="sidebar-btn"]
        # 为了兼容之前的QSS (QPushButton.sidebar-btn)，我们这里不做额外操作，
        # 而是依赖于稍后我将修改QSS去匹配 objectName 或者 dynamic property。
        # 实际上，PyQt5 QSS的 ClassName 选择器匹配的是 Python 类名。
        # 所以我必须在这里给按钮设置一个特殊的类或者 ObjectName。
        # 我将使用 setObjectName 配合 QSS ID 选择器 #sidebar-btn 
        # 但 ID 必须唯一。
        # 最好的办法是使用 property selector。
        # 我将修改 QSS 使用 QPushButton[class="sidebar-btn"]。
        # 现在先设置 property。
        btn.setCheckable(True)
        btn.clicked.connect(callback)
        btn.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(btn)
        layout.addWidget(btn)
        return btn

    def open_search_dialog(self):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, '全局搜索', '请输入搜索关键词:')
        if ok and text:
            dialog = SearchResultDialog(self, text, self.app.db_manager)
            dialog.exec_()

    def open_recycle_bin(self):
        from modules.recycle_bin import RecycleBinWindow
        dialog = RecycleBinWindow(self.app.db_manager, self)
        dialog.exec_()
        
        # 刷新所有模块数据
        if self.customer is not None: self.customer._load_customers()
        if self.business is not None: self.business._load_business()
        if self.finance is not None: self.finance._load_finance()
        if self.contract is not None: self.contract._load_contracts()

    def switch_to_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.dashboard)
        
    def switch_to_customer(self):
        if self.customer is None:
            from modules.customer import CustomerWindow
            self.customer = CustomerWindow(self.app.db_manager, self)
            self.stacked_widget.addWidget(self.customer)
            self.customer._load_customers()
        self.stacked_widget.setCurrentWidget(self.customer)
        
    def switch_to_business(self):
        if self.business is None:
            from modules.business import BusinessWindow
            self.business = BusinessWindow(self.app.db_manager, self)
            self.stacked_widget.addWidget(self.business)
            self.business._load_business()
        self.stacked_widget.setCurrentWidget(self.business)
        
    def switch_to_finance(self):
        if self.finance is None:
            from modules.finance import FinanceWindow
            self.finance = FinanceWindow(self.app.db_manager, self)
            self.stacked_widget.addWidget(self.finance)
            self.finance._load_finance()
        self.stacked_widget.setCurrentWidget(self.finance)
        
    def switch_to_contract(self):
        if self.contract is None:
            from modules.contract import ContractWindow
            self.contract = ContractWindow(self.app.db_manager, self)
            self.stacked_widget.addWidget(self.contract)
            self.contract._load_contracts()
        self.stacked_widget.setCurrentWidget(self.contract)
        
    def switch_to_work_arrangement(self):
        if self.work_arrangement is None:
            from modules.work_arrangement import WorkArrangementWindow
            self.work_arrangement = WorkArrangementWindow(self.app.db_manager, self)
            self.stacked_widget.addWidget(self.work_arrangement)
        self.stacked_widget.setCurrentWidget(self.work_arrangement)
        
    def switch_to_invoice(self):
        if self.invoice_system is None:
            from modules.invoice_system import InvoiceSystemWindow
            self.invoice_system = InvoiceSystemWindow(self)
            self.stacked_widget.addWidget(self.invoice_system)
        self.stacked_widget.setCurrentWidget(self.invoice_system)

    def switch_to_web_nav(self):
        if self.web_nav is None:
            from modules.web_nav import WebNavWindow
            self.web_nav = WebNavWindow()
            self.stacked_widget.addWidget(self.web_nav)
        self.stacked_widget.setCurrentWidget(self.web_nav)
        
    def switch_to_settings(self):
        if self.settings_window is None:
            from modules.settings import SettingsWindow
            self.settings_window = SettingsWindow(self)
            self.stacked_widget.addWidget(self.settings_window)
        self.stacked_widget.setCurrentWidget(self.settings_window)
        
    def switch_to_todo(self):
        """切换到待办事项窗口"""
        if self.todo_window is None:
            from modules.todo import TodoWindow
            self.todo_window = TodoWindow(self)
            self.stacked_widget.addWidget(self.todo_window)
        self.stacked_widget.setCurrentWidget(self.todo_window)
        
    def switch_to_notes(self):
        """切换到便签窗口"""
        if self.notes_window is None:
            from modules.notes import NotesWindow
            self.notes_window = NotesWindow(self)
            self.stacked_widget.addWidget(self.notes_window)
        self.stacked_widget.setCurrentWidget(self.notes_window)
        
    def show_backup_dialog(self):
        """显示备份/恢复对话框"""
        from dialogs.backup_restore import BackupRestoreDialog
        dialog = BackupRestoreDialog(self.app.backup_manager, self)
        dialog.exec_()
        
    def refresh_stats(self):
        """刷新首页统计数据"""
        if hasattr(self.dashboard, 'refresh_stats'):
            self.dashboard.refresh_stats()

    def closeEvent(self, event):
        """窗口关闭事件，保存窗口状态"""
        self.window_settings.setValue("geometry", self.saveGeometry())
        
        # 检查关闭行为设置
        dont_ask = self.settings.value("dont_ask_close", False, type=bool)
        close_to_tray = self.settings.value("close_to_tray", False, type=bool)
        
        if not dont_ask:
            # 弹出询问对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("关闭提示")
            dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            dialog.setFixedSize(350, 150)
            
            layout = QVBoxLayout(dialog)
            
            label = QLabel("您点击了关闭按钮，请选择操作：")
            layout.addWidget(label)
            
            # 不再询问复选框
            checkbox = QCheckBox("不再询问 (可在系统设置中更改)")
            layout.addWidget(checkbox)
            
            btn_layout = QHBoxLayout()
            minimize_btn = QPushButton("缩小到托盘")
            minimize_btn.clicked.connect(lambda: dialog.done(1)) # Return 1 for minimize
            
            exit_btn = QPushButton("退出程序")
            exit_btn.clicked.connect(lambda: dialog.done(2)) # Return 2 for exit
            
            cancel_btn = QPushButton("取消")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(minimize_btn)
            btn_layout.addWidget(exit_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            result = dialog.exec_()
            
            if result == 1: # Minimize
                close_to_tray = True
                if checkbox.isChecked():
                    self.settings.setValue("dont_ask_close", True)
                    self.settings.setValue("close_to_tray", True)
                    self.settings.sync()
            elif result == 2: # Exit
                close_to_tray = False
                if checkbox.isChecked():
                    self.settings.setValue("dont_ask_close", True)
                    self.settings.setValue("close_to_tray", False)
                    self.settings.sync()
            else: # Cancel
                event.ignore()
                return
        
        if close_to_tray:
            event.ignore()
            self.hide()
            self.tray_icon.show()
            self.tray_icon.showMessage(
                "客户资料管理系统",
                "程序已缩小到系统托盘，点击图标可还原。",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.tray_icon.hide()
            event.accept()
            # Quit application
            QCoreApplication.quit()

    def _init_tray_icon(self):
        """初始化系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        if hasattr(self.app.auth_manager, 'icon_path') and os.path.exists(self.app.auth_manager.icon_path):
            from PyQt5.QtGui import QIcon
            self.tray_icon.setIcon(QIcon(self.app.auth_manager.icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            
        # 托盘菜单
        tray_menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("退出程序", self)
        quit_action.triggered.connect(QCoreApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                if self.isMinimized():
                    self.showNormal()
                else:
                    self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def logout(self):
        """退出登录"""
        self.hide()
        # 重新显示登录窗口
        if hasattr(self.app, 'login_window'):
             self.app.login_window.show()
             # 重置登录窗口状态
             self.app.login_window.password_input.clear()
             # 重新读取记住的账号
             self.app.login_window._check_remembered_credentials()
        else:
             # 如果登录窗口被销毁了，重建一个
             from login import LoginWindow
             self.app.login_window = LoginWindow(self.app)
             self.app.login_window.show()

if __name__ == '__main__':
    logger.info("=== 应用程序启动 ===")
    try:
        app = MainApplication(sys.argv)
        logger.info("主应用程序初始化完成")
        ret = app.exec_()
        logger.info(f"应用程序退出，返回值: {ret}")
        sys.exit(ret)
    except Exception as e:
        logger.critical(f"!!! 应用程序崩溃: {str(e)}", exc_info=True)
        sys.exit(1)
