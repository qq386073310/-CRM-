from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QPushButton, QLabel, 
                             QTabWidget, QMessageBox, QMenu, QWidget)
from PyQt5.QtCore import Qt, QSize
from core.logger import logger

class RecycleBinWindow(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("回收站")
        self.resize(900, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 顶部提示
        tip_label = QLabel("提示：勾选条目进行批量操作，或右键点击条目进行单个操作")
        tip_label.setStyleSheet("color: #909399; font-style: italic;")
        layout.addWidget(tip_label)
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._load_data)
        
        # 1. 客户回收站
        self.customer_tab = self._create_table_tab("customers")
        self.tabs.addTab(self.customer_tab, "客户管理")
        
        # 2. 业务回收站
        self.business_tab = self._create_table_tab("business")
        self.tabs.addTab(self.business_tab, "业务管理")
        
        # 3. 财务回收站
        self.finance_tab = self._create_table_tab("finance")
        self.tabs.addTab(self.finance_tab, "财务记录")
        
        # 4. 合同回收站
        self.contract_tab = self._create_table_tab("contracts")
        self.tabs.addTab(self.contract_tab, "合同管理")
        
        layout.addWidget(self.tabs)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        
        # 批量操作按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)
        
        invert_btn = QPushButton("反选")
        invert_btn.clicked.connect(self._invert_selection)
        btn_layout.addWidget(invert_btn)
        
        restore_btn = QPushButton("批量恢复")
        restore_btn.clicked.connect(self._batch_restore)
        btn_layout.addWidget(restore_btn)
        
        delete_btn = QPushButton("批量删除")
        delete_btn.setStyleSheet("color: white; background-color: #f56c6c;")
        delete_btn.clicked.connect(self._batch_delete)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def _create_table_tab(self, table_type):
        """创建包含表格的标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, t=table, type=table_type: self._show_context_menu(pos, t, type)
        )
        
        # 设置列头
        if table_type == "customers":
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["ID", "公司名称", "联系人", "删除时间"])
        elif table_type == "business":
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["ID", "公司名称", "业务名称", "删除时间"])
        elif table_type == "finance":
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["ID", "公司名称", "金额", "删除时间"])
        elif table_type == "contracts":
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["ID", "合同编号", "合同标题", "删除时间"])
            
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        layout.addWidget(table)
        
        # 保存表格引用以便刷新
        setattr(self, f"{table_type}_table", table)
        
        return tab

    def _load_data(self):
        """加载当前标签页的数据"""
        current_index = self.tabs.currentIndex()
        
        if current_index == 0:
            self._load_customers()
        elif current_index == 1:
            self._load_business()
        elif current_index == 2:
            self._load_finance()
        elif current_index == 3:
            self._load_contracts()

    def _load_customers(self):
        table = self.customers_table
        table.setRowCount(0)
        
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT id, company_name, contact_person, deleted_at FROM customers WHERE is_deleted = 1 ORDER BY deleted_at DESC")
            records = cursor.fetchall()
            
            for i, row in enumerate(records):
                table.insertRow(i)
                # ID column with checkbox
                id_item = QTableWidgetItem(str(row[0]))
                id_item.setFlags(id_item.flags() | Qt.ItemIsUserCheckable)
                id_item.setCheckState(Qt.Unchecked)
                id_item.setData(Qt.UserRole, row[0]) # Store ID
                table.setItem(i, 0, id_item)
                
                table.setItem(i, 1, QTableWidgetItem(row[1]))
                table.setItem(i, 2, QTableWidgetItem(row[2]))
                table.setItem(i, 3, QTableWidgetItem(str(row[3])))
        except Exception as e:
            logger.error(f"Load deleted customers error: {e}")

    def _load_business(self):
        table = self.business_table
        table.setRowCount(0)
        
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT id, company_name, deal_business, deleted_at FROM business WHERE is_deleted = 1 ORDER BY deleted_at DESC")
            records = cursor.fetchall()
            
            for i, row in enumerate(records):
                table.insertRow(i)
                # ID column with checkbox
                id_item = QTableWidgetItem(str(row[0]))
                id_item.setFlags(id_item.flags() | Qt.ItemIsUserCheckable)
                id_item.setCheckState(Qt.Unchecked)
                id_item.setData(Qt.UserRole, row[0])
                table.setItem(i, 0, id_item)
                
                table.setItem(i, 1, QTableWidgetItem(row[1]))
                table.setItem(i, 2, QTableWidgetItem(row[2]))
                table.setItem(i, 3, QTableWidgetItem(str(row[3])))
        except Exception as e:
            logger.error(f"Load deleted business error: {e}")

    def _load_finance(self):
        table = self.finance_table
        table.setRowCount(0)
        
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT id, company_name, amount, deleted_at FROM finance WHERE is_deleted = 1 ORDER BY deleted_at DESC")
            records = cursor.fetchall()
            
            for i, row in enumerate(records):
                table.insertRow(i)
                # ID column with checkbox
                id_item = QTableWidgetItem(str(row[0]))
                id_item.setFlags(id_item.flags() | Qt.ItemIsUserCheckable)
                id_item.setCheckState(Qt.Unchecked)
                id_item.setData(Qt.UserRole, row[0])
                table.setItem(i, 0, id_item)
                
                table.setItem(i, 1, QTableWidgetItem(row[1]))
                table.setItem(i, 2, QTableWidgetItem(f"¥{row[2]}"))
                table.setItem(i, 3, QTableWidgetItem(str(row[3])))
        except Exception as e:
            logger.error(f"Load deleted finance error: {e}")

    def _load_contracts(self):
        table = self.contracts_table
        table.setRowCount(0)
        
        try:
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT id, contract_number, title, deleted_at FROM contracts WHERE is_deleted = 1 ORDER BY deleted_at DESC")
            records = cursor.fetchall()
            
            for i, row in enumerate(records):
                table.insertRow(i)
                # ID column with checkbox
                id_item = QTableWidgetItem(str(row[0]))
                id_item.setFlags(id_item.flags() | Qt.ItemIsUserCheckable)
                id_item.setCheckState(Qt.Unchecked)
                id_item.setData(Qt.UserRole, row[0])
                table.setItem(i, 0, id_item)
                
                table.setItem(i, 1, QTableWidgetItem(row[1]))
                table.setItem(i, 2, QTableWidgetItem(row[2]))
                table.setItem(i, 3, QTableWidgetItem(str(row[3])))
        except Exception as e:
            logger.error(f"Load deleted contracts error: {e}")

    def _show_context_menu(self, pos, table, table_name):
        item = table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        record_id = table.item(row, 0).data(Qt.UserRole)
        
        menu = QMenu()
        restore_action = menu.addAction("恢复")
        delete_action = menu.addAction("永久删除")
        
        action = menu.exec_(table.mapToGlobal(pos))
        
        if action == restore_action:
            self._restore_record(table_name, record_id)
        elif action == delete_action:
            self._permanent_delete_record(table_name, record_id)

    def _restore_record(self, table_name, record_id):
        reply = QMessageBox.question(
            self, '确认恢复', 
            '确定要恢复这条记录吗?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.restore_record(table_name, record_id):
                QMessageBox.information(self, "成功", "记录已恢复")
                self._load_data()
            else:
                QMessageBox.critical(self, "错误", "恢复失败")

    def _permanent_delete_record(self, table_name, record_id):
        reply = QMessageBox.question(
            self, '确认永久删除', 
            '确定要永久删除这条记录吗?\n此操作不可撤销!',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db_manager.permanent_delete_record(table_name, record_id):
                self._load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def _get_current_table(self):
        idx = self.tabs.currentIndex()
        if idx == 0: return self.customers_table, "customers"
        elif idx == 1: return self.business_table, "business"
        elif idx == 2: return self.finance_table, "finance"
        elif idx == 3: return self.contracts_table, "contracts"
        return None, None

    def _select_all(self):
        table, _ = self._get_current_table()
        if not table: return
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def _invert_selection(self):
        table, _ = self._get_current_table()
        if not table: return
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item:
                if item.checkState() == Qt.Checked:
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)

    def _batch_restore(self):
        table, table_name = self._get_current_table()
        if not table: return
        
        ids = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        
        if not ids:
            return
            
        reply = QMessageBox.question(self, '确认恢复', f'确定要恢复选中的 {len(ids)} 条记录吗?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success_count = 0
            for record_id in ids:
                if self.db_manager.restore_record(table_name, record_id):
                    success_count += 1
            
            if success_count > 0:
                QMessageBox.information(self, "成功", f"成功恢复 {success_count} 条记录")
                self._load_data()

    def _batch_delete(self):
        table, table_name = self._get_current_table()
        if not table: return
        
        ids = []
        for i in range(table.rowCount()):
            item = table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        
        if not ids:
            return
            
        reply = QMessageBox.question(self, '确认删除', f'确定要永久删除选中的 {len(ids)} 条记录吗?\n此操作不可撤销!', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success_count = 0
            for record_id in ids:
                if self.db_manager.permanent_delete_record(table_name, record_id):
                    success_count += 1
            
            if success_count > 0:
                self._load_data()
