from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QHBoxLayout, QLabel)
from PyQt5.QtCore import Qt
from core.logger import logger

class SearchResultDialog(QDialog):
    def __init__(self, parent, query, db_manager):
        super().__init__(parent)
        self.parent_window = parent # MainWindow
        self.query = query
        self.db_manager = db_manager
        self.setWindowTitle(f"搜索结果 - '{query}'")
        self.resize(1000, 600)
        self._init_ui()
        self._perform_search()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["模块", "名称/公司", "详情", "操作"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.result_table.setColumnWidth(3, 120)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.doubleClicked.connect(self._on_item_double_clicked)
        
        layout.addWidget(self.result_table)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _perform_search(self):
        results = []
        cursor = self.db_manager.conn.cursor()
        query_param = f"%{self.query}%"
        
        # 1. Search Customers
        try:
            cursor.execute("""
                SELECT '客户管理', company_name, '联系人: ' || contact_person || ' | 电话: ' || phone, company_name 
                FROM customers 
                WHERE (company_name LIKE ? OR contact_person LIKE ? OR phone LIKE ?) AND is_deleted = 0
            """, (query_param, query_param, query_param))
            results.extend(cursor.fetchall())
        except Exception as e:
            logger.error(f"Search customers error: {e}")

        # 2. Search Business
        try:
            cursor.execute("""
                SELECT '业务管理', company_name, '业务: ' || COALESCE(business_name, '') || ' | ' || COALESCE(deal_business, ''), company_name
                FROM business
                WHERE (company_name LIKE ? OR business_name LIKE ? OR deal_business LIKE ?) AND is_deleted = 0
            """, (query_param, query_param, query_param))
            results.extend(cursor.fetchall())
        except Exception as e:
            logger.error(f"Search business error: {e}")

        # 3. Search Finance
        try:
            cursor.execute("""
                SELECT '财务记录', company_name, '备注: ' || COALESCE(notes, '') || ' | 金额: ' || COALESCE(amount, 0), company_name
                FROM finance
                WHERE (company_name LIKE ? OR notes LIKE ?) AND is_deleted = 0
            """, (query_param, query_param))
            results.extend(cursor.fetchall())
        except Exception as e:
            logger.error(f"Search finance error: {e}")

        self._populate_table(results)

    def _populate_table(self, results):
        self.result_table.setRowCount(0)
        for row_idx, row_data in enumerate(results):
            self.result_table.insertRow(row_idx)
            # Module
            self.result_table.setItem(row_idx, 0, QTableWidgetItem(row_data[0]))
            # Name
            self.result_table.setItem(row_idx, 1, QTableWidgetItem(row_data[1]))
            # Details
            self.result_table.setItem(row_idx, 2, QTableWidgetItem(row_data[2]))
            # Action (Button)
            btn = QPushButton("查看")
            btn.setStyleSheet("""
                QPushButton {
                    color: #409eff; 
                    border: none; 
                    background: transparent; 
                    font-weight: bold;
                    padding: 0px;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #66b1ff;
                }
            """)
            btn.setCursor(Qt.PointingHandCursor)
            # Use default arg to capture current value
            btn.clicked.connect(lambda checked, r=row_data: self._jump_to_module(r))
            self.result_table.setCellWidget(row_idx, 3, btn)
            
            # Store data in item for double click
            self.result_table.item(row_idx, 0).setData(Qt.UserRole, row_data)

    def _on_item_double_clicked(self, item):
        row = item.row()
        data = self.result_table.item(row, 0).data(Qt.UserRole)
        self._jump_to_module(data)

    def _jump_to_module(self, data):
        module_name = data[0]
        company_name = data[3] # We stored company_name in the 4th column of SELECT
        
        self.close()
        
        if module_name == '客户管理':
            self.parent_window.switch_to_customer()
            # We need a way to filter/search in customer module
            if hasattr(self.parent_window.customer, 'search_and_select'):
                self.parent_window.customer.search_and_select(company_name)
            else:
                 # Fallback: set text and trigger search
                 self.parent_window.customer.search_input.setText(company_name)
                 self.parent_window.customer._search_customers()
                 
        elif module_name == '业务管理':
            self.parent_window.switch_to_business()
            if hasattr(self.parent_window.business, 'search_and_select'):
                self.parent_window.business.search_and_select(company_name)
            else:
                self.parent_window.business.search_input.setText(company_name)
                self.parent_window.business._search_business()
                
        elif module_name == '财务记录':
            self.parent_window.switch_to_finance()
            if hasattr(self.parent_window.finance, 'search_and_select'):
                self.parent_window.finance.search_and_select(company_name)
