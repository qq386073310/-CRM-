from PyQt5.QtWidgets import (QComboBox, QCompleter, QWidget, QVBoxLayout, QGridLayout, QHBoxLayout,
                             QPushButton, QCheckBox, QMenu, QMessageBox, QInputDialog, QDateEdit, QCalendarWidget, QButtonGroup)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDate
import sqlite3
from core.logger import logger

class ModernDateEdit(QDateEdit):
    """
    Modern styled QDateEdit with flat calendar design
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")
        
        # Customize the calendar widget
        calendar = self.calendarWidget()
        calendar.setGridVisible(False)  # Remove grid lines
        calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader) # Remove week numbers
        calendar.setNavigationBarVisible(True)
        
        # Force inline styles to ensure modern look and fix black background issues
        calendar.setStyleSheet("""
            /* Navigation Bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar { 
                background-color: #ffffff; 
                border-bottom: 1px solid #ebeef5;
            }
            
            /* Navigation Buttons */
            QCalendarWidget QToolButton {
                color: #333333;
                background-color: transparent;
                border: none;
                border-radius: 4px; 
                margin: 3px;
                padding: 5px; 
                font-weight: bold;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #ecf5ff;
                color: #409eff;
            }
            QCalendarWidget QToolButton:pressed {
                background-color: #d9ecff;
            }
            
            /* SpinBox (Year editor) */
            QCalendarWidget QSpinBox {
                background-color: transparent;
                border: none;
                color: #333333;
                font-weight: bold;
                selection-background-color: #409eff;
                selection-color: #ffffff;
            }
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                width: 0px;
                height: 0px;
            }
            
            /* Date View */
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #ffffff;
                color: #606266;
                selection-background-color: #409eff;
                selection-color: #ffffff;
                outline: none;
                border: none;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #c0c4cc;
            }
            QCalendarWidget QAbstractItemView::item {
                border-radius: 4px;
            }
            QCalendarWidget QAbstractItemView::item:hover {
                background-color: #f5f7fa;
                color: #409eff;
            }
            QCalendarWidget QAbstractItemView::item:selected {
                background-color: #409eff;
                color: #ffffff;
            }
            
            /* Header (Mon, Tue...) */
            QCalendarWidget QHeaderView::section {
                background-color: #ffffff;
                color: #909399;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ebeef5;
                font-weight: bold;
            }
            
            /* Month Menu - Attempt to style if possible (Note: Top-level menus might rely on global QSS) */
            QMenu {
                background-color: #ffffff;
                color: #606266;
                border: 1px solid #dcdfe6;
            }
            QMenu::item:selected {
                background-color: #ecf5ff;
                color: #409eff;
            }
        """)
        
        # Set default date to today if not specified in args
        if not (args and isinstance(args[0], QDate)):
            self.setDate(QDate.currentDate())

class FilterableComboBox(QComboBox):
    """
    Generic ComboBox with fuzzy search support
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        
        # Setup completer
        self._completer = QCompleter(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setModel(self.model())
        self.setCompleter(self._completer)

    def setModel(self, model):
        super().setModel(model)
        self._completer.setModel(model)

class CustomerSelectionCombo(FilterableComboBox):
    """
    带有模糊搜索功能的客户选择下拉框
    """
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # 加载数据
        self.refresh_customers()
        
    def refresh_customers(self):
        """刷新客户列表"""
        try:
            current_text = self.currentText()
            self.clear()
            
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                # 只加载未删除的客户
                cursor.execute('SELECT company_name FROM customers WHERE is_deleted = 0 ORDER BY company_name')
                customers = [row[0] for row in cursor.fetchall()]
                
            self.addItems(customers)
            
            # 恢复之前的文本（如果存在）
            if current_text:
                index = self.findText(current_text)
                if index >= 0:
                    self.setCurrentIndex(index)
                else:
                    self.setEditText(current_text)
                    
        except Exception as e:
            logger.error(f"Failed to load customers for combo: {e}")

    def get_value(self):
        """获取当前选中的文本"""
        return self.currentText().strip()

    def set_value(self, text):
        """设置当前文本"""
        if not text:
            self.setCurrentIndex(-1)
            return
            
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            self.setEditText(text)

class SingleSelectionWidget(QWidget):
    """单选/多选标签控件（支持自定义添加/删除）"""
    selectionChanged = pyqtSignal(str)

    def __init__(self, db_manager, table_name, column_name='name', parent=None, multi_select=False, check_usage_func=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.table_name = table_name
        self.column_name = column_name
        self.multi_select = multi_select
        self.check_usage_func = check_usage_func
        
        self._init_ui()
        self._load_items()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Items container
        self.items_container = QWidget()
        self.items_layout = QGridLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(5)
        self.layout.addWidget(self.items_container)
        
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(not self.multi_select)
        
        # Add button
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(24, 24)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet("border: 1px dashed #dcdfe6; border-radius: 4px; color: #909399;")
        self.add_btn.clicked.connect(self._add_item)

    def _load_items(self):
        # Clear existing
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget and widget != self.add_btn:
                widget.deleteLater()
                
        # Remove all buttons from group
        for btn in self.button_group.buttons():
            self.button_group.removeButton(btn)

        # Load from DB
        items = []
        if self.db_manager:
            try:
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    cursor.execute(f"SELECT {self.column_name} FROM {self.table_name}")
                    items = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Failed to load items for {self.table_name}: {e}")

        # Create buttons
        row = 0
        col = 0
        max_cols = 3 
        
        for item_text in items:
            btn = QCheckBox(item_text)
            btn.setCursor(Qt.PointingHandCursor)
            
            if not self.multi_select:
                # Behave like radio button but look like checkbox (or just use checkbox logic in exclusive group)
                pass
            
            # Enable context menu for deletion
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(lambda pos, b=btn: self._show_context_menu(pos, b))
                
            self.button_group.addButton(btn)
            self.items_layout.addWidget(btn, row, col)
            
            if self.multi_select:
                btn.stateChanged.connect(self._emit_change)
            else:
                btn.clicked.connect(self._emit_change)
                
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # Add "+" button
        self.items_layout.addWidget(self.add_btn, row, col)

    def _add_item(self):
        text, ok = QInputDialog.getText(self, "添加选项", "请输入新选项名称:")
        if ok and text:
            text = text.strip()
            if not text: return
            
            try:
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    
                    # 检查是否存在
                    cursor.execute(f"SELECT id FROM {self.table_name} WHERE {self.column_name} = ?", (text,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # 检查是否有软删除字段
                        cursor.execute(f"PRAGMA table_info({self.table_name})")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        if 'is_deleted' in columns:
                            cursor.execute(f"SELECT is_deleted FROM {self.table_name} WHERE id = ?", (existing[0],))
                            row = cursor.fetchone()
                            if row and row[0]:
                                # 恢复已删除的项
                                cursor.execute(f"UPDATE {self.table_name} SET is_deleted = 0 WHERE id = ?", (existing[0],))
                                self._load_items()
                                return
                        
                        QMessageBox.warning(self, "提示", "该选项已存在，请勿重复添加")
                        return

                    cursor.execute(f"INSERT INTO {self.table_name} ({self.column_name}) VALUES (?)", (text,))
                self._load_items()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加失败: {e}")

    def set_selected(self, value):
        # Reset all
        if self.button_group.exclusive():
            # For exclusive group, unchecking is tricky if we don't find the button.
            # But setChecked(True) on one will uncheck others.
            pass
        else:
            for btn in self.button_group.buttons():
                btn.setChecked(False)

        selected_values = []
        if isinstance(value, str):
            if self.multi_select:
                selected_values = value.split(',')
            else:
                selected_values = [value]
        elif isinstance(value, (list, tuple)):
            selected_values = list(value)
            
        selected_values = [str(v).strip() for v in selected_values if v]
        
        for btn in self.button_group.buttons():
            if btn.text() in selected_values:
                btn.setChecked(True)

    def get_selected(self):
        selected = []
        for btn in self.button_group.buttons():
            if btn.isChecked():
                selected.append(btn.text())
        
        if self.multi_select:
            return selected
        else:
            return selected[0] if selected else None
            
    def _emit_change(self):
        val = self.get_selected()
        if isinstance(val, list):
            self.selectionChanged.emit(",".join(val))
        else:
            self.selectionChanged.emit(val or "")

    def _show_context_menu(self, pos, btn):
        menu = QMenu(self)
        delete_action = menu.addAction("删除")
        action = menu.exec_(btn.mapToGlobal(pos))
        
        if action == delete_action:
            self._delete_item(btn.text())

    def _delete_item(self, text):
        # 1. Check usage
        if self.check_usage_func:
            msg = self.check_usage_func(text)
            if msg:
                QMessageBox.warning(self, "无法删除", msg)
                return

        # 2. Confirm
        if QMessageBox.question(self, "确认", f"确定要删除 '{text}' 吗？", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        # 3. Delete
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute(f"DELETE FROM {self.table_name} WHERE {self.column_name} = ?", (text,))
            self._load_items()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败: {e}")
