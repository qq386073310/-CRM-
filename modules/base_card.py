from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
                             QPushButton, QMenu, QGridLayout, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal

class BaseCardWidget(QFrame):
    """
    通用卡片基类，封装了选中、右键菜单、悬停等通用逻辑。
    子类需要实现 _init_ui 来填充具体内容。
    """
    
    # 信号
    selectionChanged = pyqtSignal(bool) # 选中状态改变
    
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.callbacks = {} # 存储回调函数: 'edit', 'delete'
        self.setProperty("class", "card") # 默认样式类
        
        # 初始化布局容器
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)
        
        # 内部状态
        self._is_checked = False
        
        # 子类需在 _init_ui 中向 main_layout 添加内容
        self._init_ui()
        
    def _init_ui(self):
        """子类必须重写此方法以初始化UI"""
        raise NotImplementedError("Subclasses must implement _init_ui")
        
    def set_callback(self, name, func):
        """设置回调函数"""
        self.callbacks[name] = func
        
    def contextMenuEvent(self, event):
        """通用右键菜单"""
        menu = QMenu(self)
        
        # 编辑
        edit_action = menu.addAction("编辑")
        edit_action.triggered.connect(lambda: self.callbacks.get('edit', lambda x: None)(self.data))
        
        # 删除
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.callbacks.get('delete', lambda x: None)(self.data))
        
        # 子类可以重写 _extend_context_menu 来添加更多菜单项
        self._extend_context_menu(menu)
        
        menu.exec_(event.globalPos())
        
    def _extend_context_menu(self, menu):
        """子类可重写此方法扩展右键菜单"""
        pass
        
    def set_checked(self, checked):
        """设置选中状态"""
        if self._is_checked != checked:
            self._is_checked = checked
            # 如果子类有 select_checkbox，同步状态
            if hasattr(self, 'select_checkbox'):
                self.select_checkbox.setChecked(checked)
            
            # 更新样式（可选，如果需要视觉反馈）
            self.setProperty("checked", checked)
            self.style().unpolish(self)
            self.style().polish(self)
            
            self.selectionChanged.emit(checked)
            
    def is_checked(self):
        return self._is_checked
        
    def mouseDoubleClickEvent(self, event):
        """双击触发编辑"""
        if event.button() == Qt.LeftButton:
            self.callbacks.get('edit', lambda x: None)(self.data)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """点击处理"""
        if event.button() == Qt.LeftButton:
            # 可以在这里处理点击选中逻辑，或者交给外部 QListWidget 处理
            pass
        super().mousePressEvent(event)

    # --- 辅助方法 ---
    
    def create_checkbox(self):
        """创建标准复选框"""
        cb = QCheckBox()
        cb.setFocusPolicy(Qt.NoFocus)
        cb.setChecked(self._is_checked)
        # 连接信号
        cb.toggled.connect(self._on_checkbox_toggled)
        self.select_checkbox = cb
        return cb
        
    def _on_checkbox_toggled(self, checked):
        self._is_checked = checked
        self.selectionChanged.emit(checked)
        
    def create_status_label(self, text, bg_color, text_color='#FFFFFF'):
        """创建标准状态标签"""
        label = QLabel(text)
        label.setStyleSheet(f"""
            background-color: {bg_color}; 
            color: {text_color}; 
            padding: 4px 8px; 
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        """)
        label.setFixedWidth(60) # 稍微宽一点
        label.setAlignment(Qt.AlignCenter)
        return label
        
    def create_info_row(self, label_text, value_text, icon=None):
        """创建一行信息 (Label: Value)"""
        # 简单布局，子类通常使用 GridLayout，这里仅供参考
        pass

    def create_action_btn(self, text, color_class, callback_key):
        """创建操作按钮"""
        btn = QPushButton(text)
        btn.setProperty("class", f"{color_class} small-btn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                padding: 2px 5px;
                font-size: 11px;
                border-radius: 3px;
                min-width: 40px;
            }
        """)
        if callback_key:
             # 注意：这里需要 lambda 捕获
             btn.clicked.connect(lambda: self._handle_custom_action(callback_key))
        return btn

    def _handle_custom_action(self, key):
        if key in self.callbacks:
            self.callbacks[key](self.data)
