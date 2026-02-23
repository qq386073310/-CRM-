import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QPushButton,
    QFileDialog, QLabel, QListWidget, QMessageBox, QProgressBar,
    QLineEdit, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from core.backup import BackupManager

class BackupRestoreDialog(QDialog):
    """备份恢复对话框"""
    
    def __init__(self, backup_manager: BackupManager, parent=None):
        super().__init__(parent)
        self.backup_manager = backup_manager
        self.setWindowTitle("数据备份与恢复")
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
        
    def setup_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 备份选项卡
        self.backup_tab = QWidget()
        self.setup_backup_tab()
        self.tab_widget.addTab(self.backup_tab, "备份")
        
        # 恢复选项卡
        self.restore_tab = QWidget()
        self.setup_restore_tab()
        self.tab_widget.addTab(self.restore_tab, "恢复")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def setup_backup_tab(self):
        """设置备份选项卡"""
        layout = QVBoxLayout()
        
        # 备份路径选择
        self.backup_path_label = QLabel("备份目录:")
        layout.addWidget(self.backup_path_label)
        
        self.backup_path_edit = QLabel(self.backup_manager.backup_dir)
        layout.addWidget(self.backup_path_edit)
        
        self.browse_backup_btn = QPushButton("选择目录...")
        self.browse_backup_btn.clicked.connect(self.select_backup_dir)
        layout.addWidget(self.browse_backup_btn)
        
        # 文件列表
        self.file_list_label = QLabel("将备份以下文件:")
        layout.addWidget(self.file_list_label)
        
        self.file_list = QListWidget()
        self.file_list.addItems([
            "data/app_data.db",
            "data/business.db",
            "data/app_data.db-wal",
            "data/app_data.db-shm"
        ])
        layout.addWidget(self.file_list)
        
        # 进度条
        self.backup_progress = QProgressBar()
        self.backup_progress.setRange(0, 100)
        self.backup_progress.setValue(0)
        layout.addWidget(self.backup_progress)
        
        # 备份按钮
        self.backup_btn = QPushButton("开始备份")
        self.backup_btn.clicked.connect(self.start_backup)
        layout.addWidget(self.backup_btn)
        
        self.backup_tab.setLayout(layout)
    
    def setup_restore_tab(self):
        """设置恢复选项卡"""
        layout = QVBoxLayout()
        
        # 手动恢复说明
        instructions = QLabel("""
        <h2>自动备份说明:</h2>
        <ul>
            <li><strong>触发机制:</strong> 每次关闭程序时自动执行备份</li>
            <li><strong>清理策略:</strong> 仅保留最近7天的备份文件，过期自动清理</li>
        </ul>

        <h2>手动恢复步骤:</h2>
        <ol>
            <li>完全退出本应用程序</li>
            <li>打开软件根目录下的 data 目录</li>
            <li>删除该目录下的所有文件</li>
            <li>解压备份ZIP文件到 data 目录</li>
            <li>重新启动应用程序</li>
        </ol>
        
        <h3>注意事项:</h3>
        <ul>
            <li>恢复前请确保应用程序已完全退出</li>
            <li>建议先手动执行一次备份再进行恢复</li>
        </ul>
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # 选择备份文件
        file_layout = QHBoxLayout()
        self.restore_file_edit = QLineEdit()
        self.restore_file_edit.setPlaceholderText("选择备份ZIP文件")
        file_layout.addWidget(self.restore_file_edit)
        
        self.browse_restore_btn = QPushButton("选择文件...")
        self.browse_restore_btn.clicked.connect(self.select_restore_file)
        file_layout.addWidget(self.browse_restore_btn)
        layout.addLayout(file_layout)
        
        # 进度条
        self.restore_progress = QProgressBar()
        self.restore_progress.setRange(0, 100)
        self.restore_progress.setValue(0)
        layout.addWidget(self.restore_progress)
        
        # 恢复按钮
        self.restore_btn = QPushButton("开始恢复")
        self.restore_btn.clicked.connect(self.start_restore)
        layout.addWidget(self.restore_btn)
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn, alignment=Qt.AlignCenter)
        
        self.restore_tab.setLayout(layout)
    
    def select_restore_file(self):
        """选择备份文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", "", "备份文件 (*.zip);;所有文件 (*)"
        )
        if file_path:
            self.restore_file_edit.setText(file_path)
    
    def select_backup_dir(self):
        """选择备份目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择备份目录", self.backup_manager.backup_dir
        )
        if dir_path:
            self.backup_path_edit.setText(dir_path)
    
    def start_backup(self):
        """开始备份"""
        backup_dir = self.backup_path_edit.text()
        if not backup_dir:
            QMessageBox.warning(self, "警告", "请选择备份目录")
            return
            
        # 创建备份线程
        self.backup_thread = BackupThread(
            self.backup_manager, 
            backup_dir=backup_dir
        )
        self.backup_thread.progress_updated.connect(
            self.backup_progress.setValue
        )
        self.backup_thread.finished.connect(self.on_backup_finished)
        self.backup_thread.start()
        
        self.backup_btn.setEnabled(False)
    
    def start_restore(self):
        """开始恢复"""
        backup_path = self.restore_file_edit.text()
        if not backup_path or not os.path.exists(backup_path):
            QMessageBox.warning(self, "警告", "请选择有效的备份文件")
            return
            
        # 确认恢复
        reply = QMessageBox.question(
            self, "确认", 
            "恢复操作将覆盖现有数据库文件，是否继续?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        # 创建恢复线程
        self.restore_thread = RestoreThread(
            self.backup_manager,
            backup_path=backup_path
        )
        self.restore_thread.progress_updated.connect(
            self.restore_progress.setValue
        )
        self.restore_thread.finished.connect(self.on_restore_finished)
        self.restore_thread.start()
        
        self.restore_btn.setEnabled(False)
    
    def on_backup_finished(self, success, message):
        """备份完成处理"""
        self.backup_btn.setEnabled(True)
        self.backup_progress.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)
    
    def on_restore_finished(self, success, message):
        """恢复完成处理"""
        self.restore_btn.setEnabled(True)
        self.restore_progress.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "错误", message)

class BackupThread(QThread):
    """备份线程"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, backup_manager, backup_dir=None):
        super().__init__()
        self.backup_manager = backup_manager
        self.backup_dir = backup_dir
    
    def run(self):
        try:
            backup_path = self.backup_manager.create_backup(self.backup_dir)
            if backup_path:
                self.finished.emit(True, f"备份成功创建: {backup_path}")
            else:
                self.finished.emit(False, "备份创建失败")
        except Exception as e:
            self.finished.emit(False, str(e))

class RestoreThread(QThread):
    """恢复线程"""
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, backup_manager, backup_path=None):
        super().__init__()
        self.backup_manager = backup_manager
        self.backup_path = backup_path
    
    def run(self):
        try:
            success = self.backup_manager.restore_backup(self.backup_path)
            if success:
                self.finished.emit(True, "数据库恢复成功")
            else:
                self.finished.emit(False, "数据库恢复失败")
        except Exception as e:
            self.finished.emit(False, str(e))
