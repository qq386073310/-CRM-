from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QFormLayout, QDialog,
                             QMessageBox, QHeaderView, QFileDialog, QScrollArea,
                             QFrame, QListWidget, QListWidgetItem, QGridLayout,
                             QSizePolicy, QAbstractItemView, QCheckBox, QGroupBox)
from PyQt5.QtCore import Qt, QSettings, QSize
from PyQt5.QtGui import QIcon, QIntValidator
import sqlite3
import math
from core.logger import logger
from datetime import datetime
from core.import_export import BaseImporterExporter, ImportExportError
from core.async_utils import Worker, QThreadPool
from modules.base_card import BaseCardWidget
from core.constants import CUSTOMER_STATUS_COLORS

class CustomerCardWidget(BaseCardWidget):
    """客户卡片控件"""
    
    def _init_ui(self):
        # Set fixed size for the card to ensure buttons fit
        self.setFixedSize(360, 170)
        
        # 统一边距
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(8)
        
        # 1. 顶部：公司名称 + 状态
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(self.create_checkbox())
        
        # 公司名称
        company_label = QLabel(self.data.get('company_name', ''))
        company_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        company_label.setWordWrap(True)
        top_layout.addWidget(company_label, 1) # 伸缩因子1
        
        # 状态标签
        status = self.data.get('status', '潜在')
        
        # 状态样式配置
        if status in CUSTOMER_STATUS_COLORS:
            base_color = CUSTOMER_STATUS_COLORS[status]
            if status == '成交':
                bg_color = base_color
                text_color = '#FFFFFF'
            elif status == '流失':
                bg_color = base_color
                text_color = '#FFFFFF'
            elif status == '跟进':
                bg_color = base_color
                text_color = '#000000'
            else: # 潜在
                bg_color = f"{base_color}1A"
                text_color = base_color
        else:
             # Default fallback
             base_color = '#409EFF'
             bg_color = f"{base_color}1A"
             text_color = base_color

        status_label = self.create_status_label(status, bg_color, text_color)
        status_label.setFixedWidth(50) # 固定宽度保持整齐
        top_layout.addWidget(status_label)
        
        self.main_layout.addLayout(top_layout)
        
        # 2. 中部：联系信息
        info_layout = QGridLayout()
        info_layout.setSpacing(5)
        
        # 联系人
        contact_icon = QLabel("👤")
        contact_val = QLabel(self.data.get('contact_person', '-') or '-')
        info_layout.addWidget(contact_icon, 0, 0)
        info_layout.addWidget(contact_val, 0, 1)
        
        # 电话
        phone_icon = QLabel("📞")
        phone_val = QLabel(self.data.get('phone', '-') or '-')
        info_layout.addWidget(phone_icon, 1, 0)
        info_layout.addWidget(phone_val, 1, 1)
        
        info_layout.setColumnStretch(1, 1)
        self.main_layout.addLayout(info_layout)
        
        self.main_layout.addStretch()

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame)
        line.setFixedHeight(1)
        line.setProperty("class", "separator")
        self.main_layout.addWidget(line)
        
        # 3. 底部：操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        
        # 跳转组
        btn_layout.addWidget(self.create_action_btn("业务", "success", "business"))
        btn_layout.addWidget(self.create_action_btn("合同", "primary", "contract"))
        btn_layout.addWidget(self.create_action_btn("财务", "warning", "finance"))
        btn_layout.addWidget(self.create_action_btn("文件", "info", "file"))
        
        btn_layout.addStretch() # 中间弹簧
        
        # 管理组
        btn_layout.addWidget(self.create_action_btn("编辑", "primary", "edit"))
        btn_layout.addWidget(self.create_action_btn("删除", "danger", "delete"))
        
        self.main_layout.addLayout(btn_layout)



class CustomerEditDialog(QDialog):
    """客户编辑对话框"""
    def __init__(self, db_manager, data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.data = data
        self.setWindowTitle('新增客户' if not data else '编辑客户')
        self.setFixedSize(550, 500)
        self._init_ui()
        if data:
            self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(15)
        
        basic_layout.addWidget(QLabel("公司名称*:"), 0, 0)
        self.company_name = QLineEdit()
        self.company_name.setPlaceholderText("请输入公司名称")
        basic_layout.addWidget(self.company_name, 0, 1, 1, 3)

        basic_layout.addWidget(QLabel("联系人:"), 1, 0)
        self.contact_person = QLineEdit()
        basic_layout.addWidget(self.contact_person, 1, 1)
        
        basic_layout.addWidget(QLabel("职位:"), 1, 2)
        self.position = QLineEdit()
        basic_layout.addWidget(self.position, 1, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 2. 联系方式
        contact_group = QGroupBox("联系方式")
        contact_layout = QGridLayout()
        contact_layout.setSpacing(15)
        
        contact_layout.addWidget(QLabel("座机:"), 0, 0)
        self.phone = QLineEdit()
        contact_layout.addWidget(self.phone, 0, 1)
        
        contact_layout.addWidget(QLabel("手机:"), 0, 2)
        self.mobile = QLineEdit()
        contact_layout.addWidget(self.mobile, 0, 3)
        
        contact_layout.addWidget(QLabel("邮箱:"), 1, 0)
        self.email = QLineEdit()
        contact_layout.addWidget(self.email, 1, 1, 1, 3)
        
        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)

        # 3. 状态与备注
        other_group = QGroupBox("状态与备注")
        other_layout = QGridLayout()
        other_layout.setSpacing(15)
        
        other_layout.addWidget(QLabel("状态:"), 0, 0)
        self.status = QComboBox()
        self.status.addItems(['潜在', '跟进', '成交', '流失'])
        other_layout.addWidget(self.status, 0, 1)
        
        other_layout.addWidget(QLabel("备注:"), 1, 0)
        self.notes = QLineEdit()
        other_layout.addWidget(self.notes, 1, 1)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)

        layout.addStretch()

        # 4. 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton('保存')
        self.save_btn.setProperty("class", "success")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save)
        
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)

    def _load_data(self):
        self.company_name.setText(str(self.data[0] or ''))
        self.contact_person.setText(str(self.data[1] or ''))
        self.phone.setText(str(self.data[2] or ''))
        self.status.setCurrentText(str(self.data[3] or ''))
        self.notes.setText(str(self.data[4] or ''))
        # Handle optional fields
        if len(self.data) > 5:
            self.position.setText(str(self.data[5] or ''))
            self.mobile.setText(str(self.data[6] or ''))
            self.email.setText(str(self.data[7] or ''))

    def _save(self):
        company_name = self.company_name.text().strip()
        if not company_name:
            QMessageBox.warning(self, '提示', '请填写公司名称')
            return

        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                
                if self.data:
                    # Update existing
                    # Need original company name to find ID? Or pass ID in data?
                    # The current implementation passes data tuple.
                    # existing_data[0] is company_name (used as key previously, but risky if name changes)
                    # Let's find ID by original company name first
                    cursor.execute('SELECT id FROM customers WHERE company_name = ?', (self.data[0],))
                    row = cursor.fetchone()
                    if not row:
                        raise Exception("找不到原记录")
                    customer_id = row[0]
                    
                    cursor.execute('''
                        UPDATE customers SET 
                            company_name = ?, contact_person = ?, phone = ?, 
                            status = ?, notes = ?, position = ?, mobile = ?, email = ?
                        WHERE id = ?
                    ''', (
                        company_name, self.contact_person.text(), self.phone.text(),
                        self.status.currentText(), self.notes.text(), 
                        self.position.text(), self.mobile.text(), self.email.text(),
                        customer_id
                    ))
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO customers (
                            company_name, contact_person, phone, status, 
                            notes, position, mobile, email, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ''', (
                        company_name, self.contact_person.text(), self.phone.text(),
                        self.status.currentText(), self.notes.text(), 
                        self.position.text(), self.mobile.text(), self.email.text()
                    ))
                
                self.db_manager.conn.commit()
                self.accept()
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                QMessageBox.warning(self, '错误', '公司名称已存在')
            else:
                QMessageBox.warning(self, '错误', f'保存失败: {str(e)}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败: {str(e)}')
            logger.error(f"Error saving customer: {e}")

class CustomerWindow(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.db_manager = db_manager
        self.settings = QSettings("CustomerManagement", "CustomerWindow")
        
        # Pagination state
        self.page = 1
        self.page_size = 20
        self.total_pages = 1
        self.total_count = 0
        self.pending_select_query = None
        self.threadpool = QThreadPool()
        
        self._init_ui()
        self._load_customers()
        
    def _init_ui(self):
        """初始化客户管理界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 顶部操作区域 (卡片样式)
        top_frame = QFrame()
        top_frame.setProperty("class", "card")
        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(10)

        # 路径设置工具栏
        path_toolbar = QHBoxLayout()
        path_label = QLabel("客户资料路径:")
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("请输入客户资料存储路径")
        save_path_btn = QPushButton("保存路径")
        save_path_btn.setProperty("class", "primary")
        save_path_btn.clicked.connect(self._save_path)
        
        # 加载保存的路径
        saved_path = self.settings.value("customer_data_path", "")
        if saved_path:
            self.path_input.setText(saved_path)

        path_toolbar.addWidget(path_label)
        path_toolbar.addWidget(self.path_input)
        path_toolbar.addWidget(save_path_btn)
        top_layout.addLayout(path_toolbar)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索客户...')
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar_layout.addWidget(self.search_input)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(['所有状态', '潜在', '跟进', '成交', '流失'])
        self.status_filter.currentIndexChanged.connect(self._on_filter_changed)
        toolbar_layout.addWidget(self.status_filter)

        # 排序下拉框
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            '默认排序',
            '创建时间 (新→旧)',
            '创建时间 (旧→新)',
            '公司名称 (A→Z)',
            '公司名称 (Z→A)'
        ])
        # 设置下拉列表的最小宽度
        self.sort_combo.view().setMinimumWidth(150)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        toolbar_layout.addWidget(self.sort_combo)
        
        add_btn = QPushButton('新增客户')
        add_btn.setProperty("class", "success")
        add_btn.clicked.connect(self._show_add_dialog)
        toolbar_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton('刷新')
        refresh_btn.setProperty("class", "primary")
        refresh_btn.clicked.connect(self._refresh_data)
        toolbar_layout.addWidget(refresh_btn)
        
        import_btn = QPushButton('导入')
        import_btn.setProperty("class", "info")
        try:
            import_btn.clicked.connect(self._import_customers)
        except AttributeError:
            # 兼容旧环境，使用别名方法
            import_btn.clicked.connect(self.import_customers)
        toolbar_layout.addWidget(import_btn)
        
        export_btn = QPushButton('导出')
        export_btn.setProperty("class", "info")
        try:
            export_btn.clicked.connect(self._export_customers)
        except AttributeError:
            export_btn.clicked.connect(self.export_customers)
        toolbar_layout.addWidget(export_btn)
        
        top_layout.addLayout(toolbar_layout)
        main_layout.addWidget(top_frame)
        
        # 客户列表区域 (卡片样式)
        list_frame = QFrame()
        list_frame.setProperty("class", "card")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(12, 12, 12, 12)

        batch_layout = QHBoxLayout()
        select_all_btn = QPushButton('全选')
        select_all_btn.clicked.connect(self.select_all_customers_action)
        invert_btn = QPushButton('反选')
        invert_btn.clicked.connect(self._invert_selection_customers)
        clear_btn = QPushButton('取消选择')
        clear_btn.clicked.connect(self._clear_selection_customers)
        delete_selected_btn = QPushButton('删除选中')
        delete_selected_btn.setProperty("class", "danger")
        delete_selected_btn.clicked.connect(self._delete_selected_customers)
        batch_layout.addWidget(select_all_btn)
        batch_layout.addWidget(invert_btn)
        batch_layout.addWidget(clear_btn)
        batch_layout.addWidget(delete_selected_btn)
        list_layout.addLayout(batch_layout)

        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setSpacing(12) # 卡片间距
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setViewMode(QListWidget.IconMode) # 图标模式实现网格布局
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setWordWrap(True)
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        # 设置每个item的大小提示，确保grid对齐
        # 使用IconMode配合Adjust模式，可以实现响应式网格布局
        # 设置适当的间距
        self.list_widget.setSpacing(12)
        self.list_widget.setGridSize(QSize(372, 186))
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: transparent;
                border: none;
            }
            QListWidget::item:hover {
                background-color: transparent;
                border: none;
            }
        """)
        
        list_layout.addWidget(self.list_widget)
        
        # Pagination Controls
        pagination_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.setFixedWidth(80)
        self.prev_btn.clicked.connect(self._prev_page)
        
        self.next_btn = QPushButton("下一页")
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self._next_page)
        
        self.page_label = QLabel("第 1 页 / 共 1 页")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        # 跳转控件
        jump_container = QWidget()
        jump_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        jump_layout = QHBoxLayout(jump_container)
        jump_layout.setContentsMargins(0, 0, 0, 0)
        jump_layout.setSpacing(2)
        
        lbl_jump = QLabel("跳转至")
        lbl_jump.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        jump_layout.addWidget(lbl_jump)
        
        self.jump_input = QLineEdit()
        self.jump_input.setFixedSize(50, 26)
        self.jump_input.setAlignment(Qt.AlignCenter)
        self.jump_input.setValidator(QIntValidator(1, 9999))
        self.jump_input.returnPressed.connect(self._jump_to_page)
        jump_layout.addWidget(self.jump_input)
        
        lbl_page = QLabel("页")
        lbl_page.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        jump_layout.addWidget(lbl_page)
        
        jump_btn = QPushButton("Go")
        jump_btn.setFixedSize(30, 26)
        jump_btn.setCursor(Qt.PointingHandCursor)
        jump_btn.setStyleSheet("QPushButton { min-width: 30px; max-width: 30px; padding: 0px; margin: 0px; }")
        jump_btn.clicked.connect(self._jump_to_page)
        jump_layout.addWidget(jump_btn)

        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addSpacing(5)
        pagination_layout.addWidget(jump_container)
        pagination_layout.addStretch()
        
        list_layout.addLayout(pagination_layout)
        
        main_layout.addWidget(list_frame)
        
        self.setLayout(main_layout)

    

    def _populate_list(self, customers_data):
        """填充客户列表"""
        self.list_widget.clear()
        
        for data in customers_data:
            # 创建卡片
            card = CustomerCardWidget(data)
            
            # 绑定事件
            card.set_callback('business', lambda d: self._open_business_page(d['company_name']))
            card.set_callback('contract', lambda d: self._open_contract_page(d['company_name']))
            card.set_callback('finance', lambda d: self._open_finance_page(d['company_name']))
            card.set_callback('file', lambda d: self._open_customer_folder(d['company_name']))
            card.set_callback('edit', lambda d: self._edit_customer(d))
            card.set_callback('delete', lambda d: self._delete_customer(d))
            
            # 创建列表项
            item = QListWidgetItem(self.list_widget)
            # 设置固定的卡片大小，使IconMode可以正确排列
            item.setSizeHint(QSize(360, 170)) 
            item.setData(Qt.UserRole, data) # 存储数据用于搜索筛选
            
            self.list_widget.setItemWidget(item, card)

    def _fetch_data_worker(self, search_text, status_filter, sort_option, limit, offset):
        """Background worker to fetch data and count"""
        conn = self.db_manager.create_new_connection()
        try:
            cursor = conn.cursor()
            
            # Base query
            where_clauses = ["is_deleted = 0"]
            params = []
            
            if search_text:
                where_clauses.append("(company_name LIKE ? OR contact_person LIKE ? OR phone LIKE ?)")
                search_param = f"%{search_text}%"
                params.extend([search_param, search_param, search_param])
                
            if status_filter and status_filter != '所有状态':
                where_clauses.append("status = ?")
                params.append(status_filter)
                
            where_sql = " AND ".join(where_clauses)
            
            # Count
            count_sql = f"SELECT COUNT(*) FROM customers WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # Determine Order
            order_by = "id DESC" # Default fallback
            if sort_option == '创建时间 (新→旧)':
                order_by = "id DESC"
            elif sort_option == '创建时间 (旧→新)':
                order_by = "id ASC"
            elif sort_option == '公司名称 (A→Z)':
                order_by = "company_name ASC"
            elif sort_option == '公司名称 (Z→A)':
                order_by = "company_name DESC"
            elif sort_option == '默认排序':
                order_by = "company_name ASC" # Original default was ORDER BY company_name

            # Data
            data_sql = f"""
                SELECT id, company_name, contact_person, phone, status, notes, position, mobile, email 
                FROM customers 
                WHERE {where_sql} 
                ORDER BY {order_by} 
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, params + [limit, offset])
            rows = cursor.fetchall()
            
            return rows, total
        finally:
            conn.close()

    def _load_customers(self):
        """Async load customers with pagination"""
        # UI state
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.list_widget.clear()
        
        # Parameters
        search_text = self.search_input.text().strip()
        status_filter = self.status_filter.currentText()
        sort_option = self.sort_combo.currentText()
        offset = (self.page - 1) * self.page_size
        
        # Start worker
        worker = Worker(self._fetch_data_worker, search_text, status_filter, sort_option, self.page_size, offset)
        worker.signals.result.connect(self._on_load_success)
        worker.signals.error.connect(self._on_load_error)
        self.threadpool.start(worker)

    def _on_load_success(self, result):
        rows, total = result
        self.total_count = total
        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        
        # Ensure page is within bounds
        if self.page > self.total_pages:
            self.page = self.total_pages
            # Reload if we were out of bounds (unless it's 0)
            if self.total_count > 0:
                self._load_customers()
                return

        customers_data = []
        for row in rows:
            customers_data.append({
                'id': row[0],
                'company_name': row[1],
                'contact_person': row[2],
                'phone': row[3],
                'status': row[4],
                'notes': row[5],
                'position': row[6],
                'mobile': row[7],
                'email': row[8]
            })
        
        self._populate_list(customers_data)
        self._update_pagination_ui()
        
        # 处理待处理的选中请求
        if self.pending_select_query:
            query = self.pending_select_query
            self.pending_select_query = None
            
            # 尝试查找匹配项
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                data = item.data(Qt.UserRole)
                if data:
                    company = data.get('company_name', '')
                    if query in company:
                        item.setSelected(True)
                        self.list_widget.setCurrentItem(item)
                        self.list_widget.scrollToItem(item)
                        # 触发选中视觉效果(如果需要)
                        card = self.list_widget.itemWidget(item)
                        if card and hasattr(card, 'set_checked'):
                            card.set_checked(True)
                        break

    def _on_load_error(self, err):
        QMessageBox.critical(self, "Error", f"Failed to load customers: {err}")
        self._update_pagination_ui()

    def _update_pagination_ui(self):
        self.page_label.setText(f"第 {self.page} 页 / 共 {self.total_pages} 页")
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.total_pages)

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_customers()

    def _next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self._load_customers()

    def _on_search_changed(self):
        self.page = 1
        self._load_customers()

    def _on_sort_changed(self):
        self.page = 1
        self._load_customers()

    def _jump_to_page(self):
        text = self.jump_input.text().strip()
        if not text:
            return
        try:
            page = int(text)
            if 1 <= page <= self.total_pages:
                self.page = page
                self._load_customers()
                self.jump_input.clear()
            else:
                QMessageBox.warning(self, "提示", f"请输入 1 到 {self.total_pages} 之间的页码")
                self.jump_input.selectAll()
                self.jump_input.setFocus()
        except ValueError:
            pass

    def _on_filter_changed(self):
        self.page = 1
        self._load_customers()
        
    def _refresh_data(self):
        self._load_customers()
        
    # Remove old synchronous methods if they exist
    def _search_customers(self):
        self._on_search_changed()

    def _filter_by_status(self):
        self._on_filter_changed()

    # _filter_items is no longer needed but we can keep it empty or remove calls to it
    def _filter_items(self):
        pass


    def select_all_customers_action(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'set_checked'):
                card.set_checked(True)
    
    def _invert_selection_customers(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'is_checked'):
                card.set_checked(not card.is_checked())
    
    def _clear_selection_customers(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'set_checked'):
                card.set_checked(False)
    
    def _delete_selected_customers(self):
        ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'is_checked') and card.is_checked():
                data = item.data(Qt.UserRole)
                if data and 'id' in data:
                    ids.append(int(data['id']))
        if not ids:
            return
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除选中的 {len(ids)} 位客户吗?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                # 使用软删除
                from datetime import datetime
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.executemany('UPDATE customers SET is_deleted = 1, deleted_at = ? WHERE id = ?', [(now, cid) for cid in ids])
            self._load_customers()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败: {str(e)}")

    def _save_path(self):
        """保存客户资料路径"""
        path = self.path_input.text().strip()
        if path:
            self.settings.setValue("customer_data_path", path)
            QMessageBox.information(self, "成功", "客户资料路径已保存")
        else:
            QMessageBox.warning(self, "错误", "请输入有效的路径")

    def _open_customer_folder(self, company_name):
        """打开客户文件夹"""
        path = self.path_input.text().strip()
        if not path:
            QMessageBox.warning(self, "错误", "请先设置客户资料路径")
            return
            
        try:
            import os
            customer_path = os.path.join(path, company_name)
            os.makedirs(customer_path, exist_ok=True)
            os.startfile(customer_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件夹:\n{str(e)}")


                
    def _open_business_page(self, company_name):
        """跳转到业务管理页面并搜索"""
        if self.main_window and hasattr(self.main_window, 'switch_to_business'):
            self.main_window.switch_to_business()
            # 延迟调用搜索，确保页面已切换
            if hasattr(self.main_window.business, 'search_and_select'):
                self.main_window.business.search_and_select(company_name)
            else:
                # 兼容旧代码，如果没有search_and_select，尝试直接设置搜索框
                if hasattr(self.main_window.business, 'search_input'):
                    self.main_window.business.search_input.setText(company_name)
                    if hasattr(self.main_window.business, '_search_business'):
                        self.main_window.business._search_business()

    def _open_contract_page(self, company_name):
        """跳转到合同管理页面并搜索"""
        if self.main_window and hasattr(self.main_window, 'switch_to_contract'):
            self.main_window.switch_to_contract()
            # 延迟调用搜索
            if hasattr(self.main_window.contract, 'search_and_select'):
                self.main_window.contract.search_and_select(company_name)
            else:
                # 兼容旧代码
                if hasattr(self.main_window.contract, 'search_input'):
                    self.main_window.contract.search_input.setText(company_name)
                    # 尝试触发搜索
                    if hasattr(self.main_window.contract, '_apply_filters'):
                        self.main_window.contract._apply_filters()

    def _open_finance_page(self, company_name):
        """跳转到财务管理页面并搜索"""
        if self.main_window and hasattr(self.main_window, 'switch_to_finance'):
            self.main_window.switch_to_finance()
            # 延迟调用搜索
            if hasattr(self.main_window.finance, 'search_and_select'):
                self.main_window.finance.search_and_select(company_name)
            else:
                 # 兼容旧代码
                if hasattr(self.main_window.finance, 'search_input'):
                    self.main_window.finance.search_input.setText(company_name)
                    # 财务页面可能是 textChanged 触发，也可能是回车，尝试触发信号
                    # FinanceWindow 的 search_input 连接了 textChanged
                    pass
                
    def _filter_items(self):
        """综合筛选（搜索+状态）"""
        search_text = self.search_input.text().lower().strip()
        status_filter = self.status_filter.currentText()
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            data = item.data(Qt.UserRole)
            if not data:
                continue
                
            # 1. 检查搜索文本
            text_match = True
            if search_text:
                company = str(data.get('company_name', '')).lower()
                person = str(data.get('contact_person', '')).lower()
                phone = str(data.get('phone', '')).lower()
                if (search_text not in company and 
                    search_text not in person and 
                    search_text not in phone):
                    text_match = False
            
            # 2. 检查状态
            status_match = True
            if status_filter != '所有状态':
                if str(data.get('status', '')) != status_filter:
                    status_match = False
            
            item.setHidden(not (text_match and status_match))

    def _search_customers(self):
        self._on_search_changed()
        
    def search_and_select(self, query):
        """外部调用搜索"""
        self.pending_select_query = query
        self.search_input.setText(query)
        # textChanged signal triggers _on_search_changed, which calls _load_customers
        
    def _filter_by_status(self):
        self._on_filter_changed()
    
    def _show_add_dialog(self, customer_data=None):
        dialog = CustomerEditDialog(self.db_manager, customer_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_customers()
    
    # 兼容旧代码的别名方法
    def show_add_dialog(self, customer_data=None):
        return self._show_add_dialog(customer_data)
    
    def import_customers(self):
        return self._import_customers()
    
    def export_customers(self):
        return self._export_customers()
            
    def _save_customer(self, dialog, company_name, contact_person, phone, status, notes, position, mobile, email, existing_data=None):

        """保存客户信息"""
        # 所有字段都是非必填的，但建议填写公司名称
        if not company_name:
            QMessageBox.warning(self, '提示', '请填写公司名称')
            return
            
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                
                if existing_data:
                    # 获取现有客户的ID
                    cursor.execute('SELECT id FROM customers WHERE company_name = ?', (existing_data[0],))
                    row = cursor.fetchone()
                    if not row:
                        raise Exception("找不到原记录")
                    customer_id = row[0]
                    
                    # 更新现有客户
                    cursor.execute('''
                        UPDATE customers SET 
                            company_name = ?,
                            contact_person = ?, 
                            phone = ?, 
                            status = ?, 
                            notes = ?,
                            position = ?,
                            mobile = ?,
                            email = ?
                        WHERE id = ?
                    ''', (company_name, contact_person, phone, status, notes, position, mobile, email, customer_id))
                else:
                    # 添加新客户
                    cursor.execute('''
                        INSERT INTO customers (company_name, contact_person, phone, status, notes, position, mobile, email, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ''', (company_name, contact_person, phone, status, notes, position, mobile, email))
                
                # 提交事务
                self.db_manager.conn.commit()
                
                dialog.accept()
                self._load_customers()
                
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                QMessageBox.warning(self, '错误', '公司名称已存在')
            else:
                QMessageBox.warning(self, '错误', f'保存失败: {str(e)}')
        except Exception as e:
            QMessageBox.critical(
                self, 
                '错误', 
                f'保存过程中发生错误: {str(e)}\n'
                '请检查数据库文件是否可写且未被其他程序占用'
            )
            # 记录详细错误日志
            import traceback
            logger.error(f"Error saving customer info: {traceback.format_exc()}")
            
    def _edit_customer(self, data):
        """编辑客户信息"""
        tuple_data = (
            data.get('company_name', ''),
            data.get('contact_person', ''),
            data.get('phone', ''),
            data.get('status', '潜在'),
            data.get('notes', ''),
            data.get('position', ''),  # 新增
            data.get('mobile', ''),    # 新增
            data.get('email', '')      # 新增
        )
        self._show_add_dialog(tuple_data)
        
    def _delete_customer(self, data):
        """删除客户"""
        company_name = data.get('company_name', '')
        
        reply = QMessageBox.question(
            self, 
            '确认删除', 
            f'确定要删除客户 "{company_name}" 吗?', 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                from datetime import datetime
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('UPDATE customers SET is_deleted = 1, deleted_at = ? WHERE company_name = ?', (now, company_name))
                
            self._load_customers()
            
    def _import_customers(self):
        """从Excel文件导入客户数据(增量导入)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择客户数据文件',
            '',
            'Excel文件 (*.xlsx)'
        )
        
        if not file_path:
            return
            
        try:
            # 初始化导入器
            importer = BaseImporterExporter()
            importer._required_columns = ['公司名称']
            importer._column_mapping = {
                '公司名称': 'company_name',
                '联系人': 'contact_person',
                '电话': 'phone',
                '状态': 'status',
                '备注': 'notes'
            }
            
            # 获取现有数据用于去重
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute('SELECT company_name FROM customers')
                existing_companies = [row[0] for row in cursor.fetchall()]
                importer.cache_existing_data(
                    [{'company_name': name} for name in existing_companies],
                    key_columns=['company_name']
                )
            
            # 从Excel导入数据
            imported_data = importer.import_from_excel(
                file_path=file_path,
                sheet_name='客户数据',
                key_columns=['company_name'],
                skip_duplicates=True
            )
            
            if not imported_data:
                QMessageBox.information(self, '导入完成', '没有可导入的数据')
                return
                
            # 准备导入数据
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            records_to_insert = []
            for row in imported_data:
                records_to_insert.append((
                    row.get('company_name', ''),
                    row.get('contact_person', ''),
                    row.get('phone', ''),
                    row.get('status', 'active'),
                    row.get('notes', ''),
                    now
                ))
            
            # 执行批量导入
            try:
                with self.db_manager.conn:
                    # 验证数据库连接
                    if not self.db_manager.conn:
                        raise Exception("数据库连接无效")
                    
                    # 验证表结构
                    cursor = self.db_manager.conn.cursor()
                    cursor.execute("PRAGMA table_info(customers)")
                    table_columns = [col[1] for col in cursor.fetchall()]
                    required_columns = ['company_name', 'contact_person', 'phone', 'status', 'notes', 'created_at']
                    missing_columns = [col for col in required_columns if col not in table_columns]
                    if missing_columns:
                        raise Exception(f"表结构不完整，缺少列: {', '.join(missing_columns)}")
                    
                    # 执行导入
                    cursor.executemany('''
                        INSERT OR IGNORE INTO customers 
                        (company_name, contact_person, phone, status, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', records_to_insert)
                    
                    inserted_count = cursor.rowcount
                    total_count = len(imported_data)
                    skipped_count = total_count - inserted_count
                    
                    # 验证导入结果
                    if inserted_count > 0:
                        cursor.execute('SELECT COUNT(*) FROM customers')
                        new_count = cursor.fetchone()[0]
                        logger.info(f"Total records after import: {new_count}")
                    
                # 刷新界面和数据
                self._load_customers()
                
                # 显示导入结果
                QMessageBox.information(
                    self,
                    '导入完成',
                    f'成功导入 {inserted_count} 条客户记录\n'
                    f'跳过 {skipped_count} 条重复记录\n'
                    f'共处理 {total_count} 条记录'
                )
                
                # 刷新首页统计数据
                try:
                    if hasattr(self.parent(), 'refresh_stats'):
                        self.parent().refresh_stats()
                except Exception as e:
                    logger.error(f"Error refreshing stats: {str(e)}")
                
            except sqlite3.Error as e:
                error_msg = f"数据库错误: {str(e)}"
                if "UNIQUE constraint failed" in str(e):
                    error_msg += "\n可能原因: 导入数据中包含重复的公司名称"
                QMessageBox.critical(self, '导入错误', error_msg)
                import traceback
                logger.error(f"Import error details:\n{traceback.format_exc()}")
            
        except ImportExportError as e:
            QMessageBox.critical(self, '导入错误', str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                '导入失败',
                f'导入过程中发生错误:\n{str(e)}\n'
                '请检查文件格式是否正确'
            )
            
    def _export_customers(self):
        """导出客户数据为Excel格式"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '导出客户数据',
            'customers.xlsx',
            'Excel文件 (*.xlsx)'
        )
        
        if not file_path:
            return
            
        try:
            # 验证数据库连接
            if not self.db_manager or not self.db_manager.conn:
                raise Exception("数据库连接未初始化")
                
            # 从数据库获取数据
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM customers')
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    QMessageBox.warning(self, '警告', '客户表中没有数据可导出')
                    return
                    
                # 获取完整的表结构信息
                cursor.execute("PRAGMA table_info(customers)")
                table_info = cursor.fetchall()
                all_columns = [col[1] for col in table_info]
                logger.debug(f"Database table structure: {all_columns}")
                
                # 确保查询所有必要字段
                required_columns = [
                    'company_name', 'contact_person', 'phone', 
                    'status', 'notes', 'created_at'
                ]
                
                # 构建查询语句，只包含实际存在的列
                select_columns = [col for col in required_columns if col in all_columns]
                if not select_columns:
                    raise Exception("没有可导出的有效列")
                    
                query = f"SELECT {','.join(select_columns)} FROM customers ORDER BY company_name"
                logger.debug(f"Executing query: {query}")
                cursor.execute(query)
                
                rows = cursor.fetchall()
                if not rows:
                    raise Exception("数据库查询返回空结果")
                
                # 转换为字典列表格式，处理NULL值
                export_data = []
                for row in rows:
                    row_data = {}
                    for idx, col in enumerate(select_columns):
                        # 将None转换为空字符串
                        row_data[col] = '' if row[idx] is None else row[idx]
                    export_data.append(row_data)
                
                logger.info(f"Retrieved {len(export_data)} records")
                
                # 准备最终导出数据
                final_data = []
                for item in export_data:
                    final_data.append({
                        '公司名称': item.get('company_name', ''),
                        '联系人': item.get('contact_person', ''),
                        '电话': item.get('phone', ''),
                        '状态': item.get('status', ''),
                        '备注': item.get('notes', ''),
                        '创建时间': item.get('created_at', '')
                    })
                
                # 使用BaseImporterExporter导出
                exporter = BaseImporterExporter()
                if not hasattr(exporter, 'export_to_excel'):
                    raise Exception("BaseImporterExporter缺少export_to_excel方法")
                    
                exporter.export_to_excel(
                    data=final_data,
                    file_path=file_path,
                    sheet_name='客户数据',
                    headers=['公司名称', '联系人', '电话', '状态', '备注', '创建时间']
                )
                
                # 验证文件是否创建成功
                import os
                if not os.path.exists(file_path):
                    raise Exception("导出文件创建失败")
                    
                file_size = os.path.getsize(file_path)
                if file_size < 1024:  # 小于1KB可能是空文件
                    raise Exception("导出文件可能为空")
                
                QMessageBox.information(
                    self, 
                    '导出成功', 
                    f'客户数据已成功导出到:\n{file_path}\n'
                    f'共导出 {len(final_data)} 条记录\n'
                    f'文件大小: {file_size/1024:.1f}KB'
                )
            
        except ImportExportError as e:
            QMessageBox.critical(self, '导出错误', 
                f'导出过程中发生错误:\n{str(e)}\n'
                '请检查Excel文件格式是否正确')
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Export error details:\n{error_details}")
            
            QMessageBox.critical(
                self, 
                '导出失败', 
                f'导出过程中发生严重错误:\n{str(e)}\n'
                '详细错误已记录到控制台\n'
                '可能原因:\n'
                '1. 数据库连接问题\n'
                '2. 磁盘空间不足\n'
                '3. 文件权限问题\n'
                '4. 数据格式错误'
            )

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = CustomerWindow(None)
    window.show()
    sys.exit(app.exec_())
