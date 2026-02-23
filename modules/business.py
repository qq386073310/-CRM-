import os
import json
from datetime import datetime
from core.import_export import BaseImporterExporter, ImportExportError
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLineEdit, QComboBox, QFormLayout, QDialog,
    QMessageBox, QHeaderView, QDateEdit, QScrollArea,
    QCheckBox, QTextEdit, QFileDialog, QGridLayout,
    QGroupBox, QFrame, QStyle, QSplitter, QButtonGroup, QSizePolicy,
    QListWidget, QListWidgetItem, QAbstractItemView, QInputDialog, QMenu
)
from PyQt5.QtCore import Qt, QDate, QTimer, QSize, QSettings, pyqtSignal, QThreadPool
from PyQt5.QtGui import QIcon, QIntValidator
import sqlite3
import math
from datetime import datetime
from utils.paths import get_app_path
from core.logger import logger
from modules.common_widgets import CustomerSelectionCombo, ModernDateEdit
from core.async_utils import Worker

class DynamicSelectionWidget(QWidget):
    """动态选择控件(支持复选和自定义添加)"""
    selectionChanged = pyqtSignal(str)

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.checkboxes = {}
        self._init_ui()
        self._load_types()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 复选框容器
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.grid_widget)
        
        # 添加按钮
        self.add_btn = QPushButton("+ 添加业务类型")
        self.add_btn.setFlat(True)
        self.add_btn.setStyleSheet("text-align: left; color: #409EFF; padding: 5px;")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_new_type)
        self.layout.addWidget(self.add_btn)

    def _load_types(self):
        # 清除现有控件
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.checkboxes = {}
        
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("SELECT name FROM business_types ORDER BY id")
                types = [row[0] for row in cursor.fetchall()]
                
                row, col = 0, 0
                for name in types:
                    cb = QCheckBox(name)
                    cb.stateChanged.connect(self._emit_change)
                    # 添加右键菜单
                    cb.setContextMenuPolicy(Qt.CustomContextMenu)
                    cb.customContextMenuRequested.connect(lambda pos, n=name: self._show_context_menu(pos, n))
                    
                    self.grid_layout.addWidget(cb, row, col)
                    self.checkboxes[name] = cb
                    col += 1
                    if col > 2: # 3列布局
                        col = 0
                        row += 1
        except Exception as e:
            logger.error(f"Failed to load business types: {e}")

    def _add_new_type(self):
        text, ok = QInputDialog.getText(self, "添加业务类型", "请输入新的业务类型名称:")
        if ok and text:
            text = text.strip()
            if not text: return
            try:
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    cursor.execute("INSERT INTO business_types (name) VALUES (?)", (text,))
                    self.db_manager.conn.commit()
                self._load_types()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加失败 (可能已存在): {e}")

    def _show_context_menu(self, pos, name):
        menu = QMenu(self)
        delete_action = menu.addAction(f"删除 '{name}'")
        action = menu.exec_(self.sender().mapToGlobal(pos))
        if action == delete_action:
            self._delete_type(name)

    def _delete_type(self, name):
        confirm = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除业务类型 '{name}' 吗？\n(不会影响已使用此类型的历史记录)", 
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    cursor.execute("DELETE FROM business_types WHERE name = ?", (name,))
                    self.db_manager.conn.commit()
                self._load_types()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {e}")

    def get_selected_items(self):
        return ",".join([name for name, cb in self.checkboxes.items() if cb.isChecked()])

    def set_selected_items(self, text):
        if not text: return
        # 先清空所有选择
        for cb in self.checkboxes.values():
            cb.setChecked(False)
            
        selected = text.split(',')
        for name in selected:
            name = name.strip()
            if name in self.checkboxes:
                self.checkboxes[name].setChecked(True)
            elif name: # 如果是以前存的但现在配置表里没有的类型，是否要显示？
                # 暂时忽略，或者自动添加到配置表？为了数据完整性，最好保留显示，但这里很难动态添加而不保存到DB。
                # 既然是动态配置，如果类型被删了，这里就选不上了。
                # 但用户说“不会影响已使用此类型的历史记录”，说明历史记录还是存着这个string。
                # 如果要显示出来，必须有一个checkbox。
                # 我们可以临时添加一个checkbox吗？
                pass

    def refresh(self):
        self._load_types()

    def _emit_change(self):
        self.selectionChanged.emit(self.get_selected_items())

from modules.base_card import BaseCardWidget
from core.constants import BUSINESS_STATUS_COLORS

class BusinessCardWidget(BaseCardWidget):
    """业务卡片控件"""
    
    def _init_ui(self):
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.create_checkbox())
        
        name_label = QLabel(self.data.get('company_name', ''))
        name_label.setProperty("class", "business-card-title")
        name_label.setWordWrap(True)
        title_layout.addWidget(name_label)
        self.main_layout.addLayout(title_layout)
        
        # 分隔线（统一为 QFrame.NoFrame + 固定高度 1px）
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame)
        line.setFixedHeight(1)
        line.setProperty("class", "separator")
        self.main_layout.addWidget(line)
        
        # 详细信息
        info_layout = QGridLayout()
        info_layout.setSpacing(5)
        
        # 业务类型
        info_layout.addWidget(QLabel("业务类型:"), 0, 0)
        biz_type = QLabel(self.data.get('business_type', self.data.get('deal_business', '-')))
        biz_type.setProperty("class", "highlight-text")
        biz_type.setWordWrap(True)
        info_layout.addWidget(biz_type, 0, 1)
        
        # 记账周期
        info_layout.addWidget(QLabel("记账周期:"), 1, 0)
        start = self.data.get('proxy_start_date', '')
        end = self.data.get('proxy_end_date', '')
        if not (start and '-' in start):
            start = ''
        if not (end and '-' in end):
            end = ''
        if start and end:
            period = f"{start} 至 {end}"
        elif start:
            period = start
        elif end:
            period = f"至 {end}"
        else:
            period = ''
        period_label = QLabel(period)
        period_label.setProperty("class", "info-text")
        period_label.setWordWrap(True)
        info_layout.addWidget(period_label, 1, 1)
        
        self.main_layout.addLayout(info_layout)
        
        # 状态 (Optional, if business has status)
        # Assuming business might have a status field in the future or now.
        # Currently no explicit status display in original code except logic implied.
        
        # Use context menu for delete, provided by BaseCardWidget
        
        # If double click logic was not present in original BusinessCardWidget (it wasn't),
        # BaseCardWidget adds it. We should ensure 'edit' callback is set in BusinessWindow.


class BusinessEditDialog(QDialog):
    """业务记录编辑对话框"""
    def __init__(self, db_manager, biz_id=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.biz_id = biz_id
        self.setWindowTitle('添加业务记录' if biz_id is None else '编辑业务记录')
        self.setFixedSize(600, 650)
        self.setup_ui()
        if self.biz_id is not None:
            self._load_business_data()

    def setup_ui(self):
        """初始化对话框UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout()
        basic_layout.setSpacing(15)
        
        # 公司名称
        basic_layout.addWidget(QLabel('公司名称*:'), 0, 0)
        self.company_name = CustomerSelectionCombo(self.db_manager)
        basic_layout.addWidget(self.company_name, 0, 1, 1, 3)
        
        # 业务名称
        basic_layout.addWidget(QLabel('业务名称*:'), 1, 0)
        self.business_name = QLineEdit()
        self.business_name.setPlaceholderText("请输入业务名称")
        basic_layout.addWidget(self.business_name, 1, 1, 1, 3)
        
        # 业务类型
        basic_layout.addWidget(QLabel('业务类型:'), 2, 0)
        self.business_type = DynamicSelectionWidget(self.db_manager)
        basic_layout.addWidget(self.business_type, 2, 1, 1, 3)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 2. 业务详情
        detail_group = QGroupBox("业务详情")
        detail_layout = QGridLayout()
        detail_layout.setSpacing(15)
        
        # 记账周期
        detail_layout.addWidget(QLabel('记账周期:'), 0, 0)
        date_layout = QHBoxLayout()
        self.proxy_start_date = ModernDateEdit(QDate.currentDate())
        self.proxy_start_date.setDisplayFormat('yyyy-MM-dd')
        
        self.proxy_end_date = ModernDateEdit(QDate.currentDate())
        self.proxy_end_date.setDisplayFormat('yyyy-MM-dd')
        
        date_layout.addWidget(self.proxy_start_date)
        date_layout.addWidget(QLabel('至'))
        date_layout.addWidget(self.proxy_end_date)
        detail_layout.addLayout(date_layout, 0, 1, 1, 3)

        # 公司密码
        detail_layout.addWidget(QLabel('公司密码:'), 1, 0)
        self.company_password = QLineEdit()
        self.company_password.setPlaceholderText("如有密码请填写")
        detail_layout.addWidget(self.company_password, 1, 1, 1, 3)
        
        detail_group.setLayout(detail_layout)
        layout.addWidget(detail_group)
        
        # 3. 其他信息
        other_group = QGroupBox("其他信息")
        other_layout = QGridLayout()
        other_layout.setSpacing(15)
        
        other_layout.addWidget(QLabel('公开信息:'), 0, 0)
        self.public_info = QTextEdit()
        self.public_info.setPlaceholderText("此处填写公开可见的信息")
        self.public_info.setMaximumHeight(60)
        other_layout.addWidget(self.public_info, 0, 1)
        
        other_layout.addWidget(QLabel('备注:'), 1, 0)
        self.remarks = QTextEdit()
        self.remarks.setPlaceholderText("内部备注信息")
        self.remarks.setMaximumHeight(60)
        other_layout.addWidget(self.remarks, 1, 1)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton('保存')
        self.save_btn.setProperty("class", "success")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_business)
        
        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)

        # 默认不选中任何公司
        self.company_name.setCurrentIndex(-1)
        if self.company_name.lineEdit():
            self.company_name.lineEdit().clear()

    def _load_customer_names(self):
        """加载客户名称列表"""
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("SELECT company_name FROM customers WHERE is_deleted = 0 ORDER BY company_name")
                names = [row[0] for row in cursor.fetchall()]
                self.company_name.addItems(names)
                self.company_name.setCurrentIndex(-1)
        except Exception as e:
            logger.error(f"Failed to load customer names: {e}")

    def _load_business_data(self):
        """加载现有业务数据"""
        def safe_parse_date(date_value):
            """安全解析日期，处理各种格式"""
            if not date_value:
                return QDate.currentDate()
                
            try:
                # 处理字符串日期
                if isinstance(date_value, str):
                    if date_value.isdigit():  # 时间戳
                        return QDate.fromString(
                            datetime.fromtimestamp(int(date_value)).strftime('%Y-%m-%d'), 
                            'yyyy-MM-dd'
                        )
                    elif '-' in date_value:  # 日期字符串
                        return QDate.fromString(date_value, 'yyyy-MM-dd')
                
                # 处理datetime对象或时间戳
                if isinstance(date_value, (int, float)):  # 时间戳
                    return QDate.fromString(
                        datetime.fromtimestamp(date_value).strftime('%Y-%m-%d'), 
                        'yyyy-MM-dd'
                    )
                    
            except Exception as e:
                logger.warning(f"Date parse warning: {e}")
            return QDate.currentDate()

        logger.info(f"Loading business data biz_id={self.biz_id}")
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                
                # 获取列名信息确保正确映射
                cursor.execute("PRAGMA table_info(business)")
                columns = [col[1] for col in cursor.fetchall()]
                logger.debug(f"Database columns: {columns}")
                
                cursor.execute(
                    'SELECT * FROM business WHERE id = ?',
                    (self.biz_id,)
                )
                row = cursor.fetchone()

                if row:
                    logger.debug(f"Database record: {row}")
                    
                    # 基础信息 - 使用列名索引更安全
                    col_idx = {col: idx for idx, col in enumerate(columns)}
                    self.company_name.setCurrentText(str(row[col_idx['company_name']]) if row[col_idx['company_name']] else '')
                    self.business_name.setText(str(row[col_idx['business_name']]) if row[col_idx['business_name']] else '')
                    
                    # 业务类型
                    b_type = ''
                    if 'business_type' in col_idx and row[col_idx['business_type']]:
                        b_type = str(row[col_idx['business_type']])
                    
                    # 兼容旧数据：如果业务类型是空的或者旧值，尝试从成交业务获取
                    if not b_type or b_type == '服务业务':
                        if row[col_idx['proxy_accounting']]:
                            b_type = '代理记账'
                        elif row[col_idx['business_agent']]:
                            b_type = '工商代办'
                        elif 'other_business' in col_idx and row[col_idx['other_business']]:
                            b_type = '其他业务'
                    
                    self.business_type.set_selected_items(b_type)
                    
                    # 二级业务/成交业务控件已移除，不再设置
                    
                    # 修复公司密码字段
                    password = str(row[col_idx['company_password']]) if row[col_idx['company_password']] else ''
                    self.company_password.setEchoMode(QLineEdit.Normal)
                    self.company_password.setText(password)
                    
                    # 改进日期处理
                    def safe_parse_date(date_value):
                        """安全解析日期，处理各种格式"""
                        if not date_value:
                            return QDate.currentDate()
                            
                        try:
                            # 处理字符串日期
                            if isinstance(date_value, str):
                                if date_value.isdigit():  # 时间戳
                                    return QDate.fromString(
                                        datetime.fromtimestamp(int(date_value)).strftime('%Y-%m-%d'), 
                                        'yyyy-MM-dd'
                                    )
                                elif '-' in date_value:  # 日期字符串
                                    return QDate.fromString(date_value, 'yyyy-MM-dd')
                            
                            # 处理datetime对象或时间戳
                            if isinstance(date_value, (int, float)):  # 时间戳
                                return QDate.fromString(
                                    datetime.fromtimestamp(date_value).strftime('%Y-%m-%d'), 
                                    'yyyy-MM-dd'
                                )
                                
                        except Exception as e:
                            logger.warning(f"Date parse warning: {e}")
                        return QDate.currentDate()

                    # 代理记账时间段
                    start_date = safe_parse_date(row[col_idx['proxy_start_date']])
                    end_date = safe_parse_date(row[col_idx['proxy_end_date']])
                    self.proxy_start_date.setDate(start_date)
                    self.proxy_end_date.setDate(end_date)
                    
                    # 修复公开信息字段
                    public_info = str(row[col_idx['public_info']]) if row[col_idx['public_info']] is not None else ''
                    self.public_info.setPlainText(public_info)
                    
                    # 备注信息
                    remarks = str(row[col_idx['remarks']]) if row[col_idx['remarks']] is not None else ''
                    self.remarks.setPlainText(remarks)
                    
                    # 业务日期字段已移除
                    
                    logger.info("Data loaded successfully")

        except sqlite3.Error as e:
            QMessageBox.critical(
                self,
                '数据库错误',
                f'加载业务数据失败: {str(e)}'
            )

    def _save_business(self):
        """保存业务记录"""
        logger.info("Starting to save business data")
        
        # 字段验证
        company_name = self.company_name.currentText().strip()
        business_name = self.business_name.text().strip()
        
        if not company_name:
            QMessageBox.warning(self, '警告', '公司名称不能为空')
            return
        if not business_name:
            QMessageBox.warning(self, '警告', '业务名称不能为空')
            return

        try:
            # 准备业务数据
            now = datetime.now()
            data = {
                'company_name': company_name,
                'business_name': business_name,
                'business_type': self.business_type.get_selected_items(),
                'secondary_business': '',
                'proxy_accounting': 0,
                'business_agent': 0,
                'other_business': '',
                'proxy_start_date': self.proxy_start_date.date().toString('yyyy-MM-dd'),
                'proxy_end_date': self.proxy_end_date.date().toString('yyyy-MM-dd'),
                'company_password': self.company_password.text().strip(),
                'public_info': self.public_info.toPlainText().strip(),
                'remarks': self.remarks.toPlainText().strip(),
                'create_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'business_date': now.strftime('%Y-%m-%d'),
                'status': 'active',
                'deal_business': ''
            }

            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                
                # 检查表结构
                cursor.execute("PRAGMA table_info(business)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # 确保 business_type 字段存在
                if 'business_type' not in columns:
                    cursor.execute("ALTER TABLE business ADD COLUMN business_type TEXT")

                if self.biz_id is None:
                    # 新增记录
                    cursor.execute('''
                        INSERT INTO business (
                            company_name, business_name, business_type,
                            secondary_business, proxy_accounting, business_agent,
                            proxy_start_date, proxy_end_date, 
                            company_password, public_info, remarks, 
                            create_time, business_date, status,
                            deal_business, other_business
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        data['company_name'], data['business_name'], data['business_type'],
                        data['secondary_business'], data['proxy_accounting'], data['business_agent'],
                        data['proxy_start_date'], data['proxy_end_date'],
                        data['company_password'], data['public_info'], data['remarks'], 
                        data['create_time'], data['business_date'], data['status'],
                        data['deal_business'], data['other_business']
                    ))
                else:
                    # 更新记录
                    cursor.execute('''
                        UPDATE business SET
                            company_name = ?, business_name = ?, business_type = ?,
                            secondary_business = ?, proxy_accounting = ?, business_agent = ?,
                            proxy_start_date = ?, proxy_end_date = ?,
                            company_password = ?, public_info = ?, remarks = ?,
                            status = ?, deal_business = ?, other_business = ?
                        WHERE id = ?
                    ''', (
                        data['company_name'], data['business_name'], data['business_type'],
                        data['secondary_business'], data['proxy_accounting'], data['business_agent'],
                        data['proxy_start_date'], data['proxy_end_date'],
                        data['company_password'], data['public_info'], data['remarks'], 
                        data['status'], data['deal_business'], data['other_business'],
                        self.biz_id
                    ))

            self.accept()

        except sqlite3.Error as e:
            QMessageBox.critical(
                self,
                '数据库错误',
                f'保存业务数据失败: {str(e)}'
            )



class BusinessWindow(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.settings = QSettings("BusinessManagement", "BusinessWindow")
        
        # Pagination state
        self.page = 1
        self.page_size = 20
        self.total_pages = 0
        self.total_records = 0
        self.pending_select_query = None
        self.threadpool = QThreadPool()
        
        self.setup_ui()
        self._check_schema()
        
        # 恢复分割器状态
        if self.settings.value("splitter_state"):
            self.splitter.restoreState(self.settings.value("splitter_state"))
        
        # 监听分割器移动，实时保存状态
        self.splitter.splitterMoved.connect(self._save_splitter_state)
            
    def _save_splitter_state(self, pos, index):
        """保存分割器状态"""
        self.settings.setValue("splitter_state", self.splitter.saveState())
            
    def closeEvent(self, event):
        """窗口关闭时保存状态"""
        self.settings.setValue("splitter_state", self.splitter.saveState())
        super().closeEvent(event)




    def setup_ui(self):
        """初始化UI界面"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # 顶部操作按钮容器 (卡片样式)
        top_frame = QFrame()
        top_frame.setProperty("class", "card")
        top_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed) # 高度固定，不随窗口变化
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 10, 10, 10)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索公司名称/业务名称...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(self._search_business)
        search_layout.addWidget(self.search_input)

        # 排序下拉框
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            '默认排序 (创建时间)',
            '创建时间 (新→旧)',
            '创建时间 (旧→新)',
            '公司名称 (A→Z)',
            '公司名称 (Z→A)'
        ])
        # 设置下拉列表的最小宽度
        self.sort_combo.view().setMinimumWidth(160)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        search_layout.addWidget(self.sort_combo)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton('新增业务')
        self.add_btn.setProperty("class", "success")
        self.add_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        self.add_btn.clicked.connect(self._add_business)
        btn_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton('刷新')
        self.refresh_btn.setProperty("class", "primary")
        self.refresh_btn.clicked.connect(self._load_business)
        btn_layout.addWidget(self.refresh_btn)

        self.import_btn = QPushButton('导入')
        self.import_btn.setProperty("class", "info")
        self.import_btn.clicked.connect(self._import_business)
        btn_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton('导出')
        self.export_btn.setProperty("class", "info")
        self.export_btn.clicked.connect(self._export_business)
        btn_layout.addWidget(self.export_btn)
        
        top_layout.addLayout(search_layout)
        top_layout.addStretch() # 中间弹簧
        top_layout.addLayout(btn_layout)
        
        self.layout.addWidget(top_frame)
        
        # 主体区域 (分割视图)
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # 左侧：列表容器 (卡片样式)
        list_frame = QFrame()
        list_frame.setProperty("class", "card")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(10, 10, 10, 10)
        
        batch_layout = QHBoxLayout()
        select_all_btn = QPushButton('全选')
        select_all_btn.clicked.connect(self._select_all_business)
        invert_btn = QPushButton('反选')
        invert_btn.clicked.connect(self._invert_selection_business)
        clear_btn = QPushButton('取消选择')
        clear_btn.clicked.connect(self._clear_selection_business)
        delete_selected_btn = QPushButton('删除选中')
        delete_selected_btn.setProperty("class", "danger")
        delete_selected_btn.clicked.connect(self._delete_selected_business)
        batch_layout.addWidget(select_all_btn)
        batch_layout.addWidget(invert_btn)
        batch_layout.addWidget(clear_btn)
        batch_layout.addWidget(delete_selected_btn)
        list_layout.addLayout(batch_layout)
        
        # 创建业务列表 (Card View)
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setSpacing(10) # 卡片间距
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)
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
        """)
        
        list_layout.addWidget(self.list_widget)
        
        # 分页控件
        pagination_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.setFixedWidth(80)
        self.prev_btn.clicked.connect(self._prev_page)
        
        self.page_label = QLabel("第 1 / 1 页")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("color: #606266; margin: 0 10px;")
        
        self.next_btn = QPushButton("下一页")
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self._next_page)
        
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
        
        self.splitter.addWidget(list_frame)
        
        # 右侧：详情编辑面板
        self.detail_frame = QFrame()
        self.detail_frame.setProperty("class", "card")
        self.detail_frame.setMinimumWidth(350)
        self._init_detail_panel()
        self.splitter.addWidget(self.detail_frame)
        
        # 设置分割比例 (4:6) - 卡片列表可以窄一点
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 6)
        
        # 初始加载数据
        self._load_business()
        
        # 连接选择信号
        self.list_widget.itemClicked.connect(self._on_list_item_clicked)

    def _init_detail_panel(self):
        """初始化右侧详情编辑面板"""
        layout = QVBoxLayout(self.detail_frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        
        title = QLabel("详细信息编辑")
        title.setProperty("class", "panel-title")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        self.form_layout = QFormLayout(content)
        self.form_layout.setSpacing(15)
        
        # 定义编辑控件
        self.edit_widgets = {}
        
        # 公司名称
        self.edit_widgets['company_name'] = QLineEdit()
        self.form_layout.addRow("公司名称:", self.edit_widgets['company_name'])
        
        # 业务名称
        self.edit_widgets['business_name'] = QLineEdit()
        self.form_layout.addRow("业务名称:", self.edit_widgets['business_name'])
        
        # 业务类型
        self.edit_widgets['business_type'] = DynamicSelectionWidget(self.db_manager)
        # 绑定选择变化事件
        self.edit_widgets['business_type'].selectionChanged.connect(lambda text: self._auto_save_field('business_type'))
        self.form_layout.addRow("业务类型:", self.edit_widgets['business_type'])
        
        # 公开信息 (多行)
        self.edit_widgets['public_info'] = QTextEdit()
        # self.edit_widgets['public_info'].setMinimumHeight(150)
        self.form_layout.addRow("公开信息:", self.edit_widgets['public_info'])
        
        # 记账周期
        period_widget = QWidget()
        period_layout = QHBoxLayout(period_widget)
        period_layout.setContentsMargins(0, 0, 0, 0)
        
        self.edit_widgets['proxy_start_date'] = ModernDateEdit(QDate.currentDate())
        self.edit_widgets['proxy_start_date'].setDisplayFormat('yyyy-MM-dd')
        self.edit_widgets['proxy_end_date'] = ModernDateEdit(QDate.currentDate())
        self.edit_widgets['proxy_end_date'].setDisplayFormat('yyyy-MM-dd')
        
        period_layout.addWidget(self.edit_widgets['proxy_start_date'])
        period_layout.addWidget(QLabel('至'))
        period_layout.addWidget(self.edit_widgets['proxy_end_date'])
        
        self.form_layout.addRow("记账周期:", period_widget)
        
        # 公司密码 (隐藏但保留)
        self.edit_widgets['company_password'] = QLineEdit()
        self.form_layout.addRow("公司密码:", self.edit_widgets['company_password'])
        
        # 备注 (隐藏但保留)
        self.edit_widgets['remarks'] = QTextEdit()
        self.form_layout.addRow("备注:", self.edit_widgets['remarks'])
        
        # 绑定单行文本自动保存事件
        for key, widget in self.edit_widgets.items():
            if isinstance(widget, QLineEdit) and key not in ['other_business_input']: # 排除复合控件中的输入框
                widget.editingFinished.connect(lambda k=key: self._auto_save_field(k))
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # 底部按钮布局
        btn_layout = QHBoxLayout()
        
        # 保存按钮 (针对多行文本)
        save_btn = QPushButton("保存修改")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save_all_details)
        btn_layout.addWidget(save_btn)
        
        # 删除按钮
        self.delete_btn = QPushButton("删除此记录")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setStyleSheet("background-color: #f56c6c; color: white;")
        self.delete_btn.clicked.connect(self._delete_current_business)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)
        
        # 初始状态禁用
        self.detail_frame.setEnabled(False)



    def _auto_save_field(self, field_key):
        """自动保存单个字段"""
        if not hasattr(self, 'current_biz_id') or not self.current_biz_id:
            return
            
        widget = self.edit_widgets[field_key]
        if isinstance(widget, QComboBox):
            new_value = widget.currentText()
        elif isinstance(widget, DynamicSelectionWidget):
            new_value = widget.get_selected_items()
        else:
            new_value = widget.text()
        
        # 更新数据库
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute(f'UPDATE business SET {field_key} = ? WHERE id = ?', (new_value, self.current_biz_id))
                self.db_manager.conn.commit()
            
            # 更新列表显示
            current_item = self.list_widget.currentItem()
            if current_item:
                data = current_item.data(Qt.UserRole)
                if field_key in data:
                    data[field_key] = new_value
                    current_item.setData(Qt.UserRole, data)
                    
                    # 重新创建卡片以刷新显示
                    new_card = BusinessCardWidget(data)
                    current_item.setSizeHint(new_card.sizeHint())
                    self.list_widget.setItemWidget(current_item, new_card)
                
            logger.debug(f"Field {field_key} auto-saved")
            
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存 {field_key}: {str(e)}")

    def _save_all_details(self):
        """保存所有详情信息"""
        if not hasattr(self, 'current_biz_id') or not self.current_biz_id:
            return
            
        try:
            # 准备数据
            data = {
            'company_name': self.edit_widgets['company_name'].text(),
            'business_name': self.edit_widgets['business_name'].text(),
            'business_type': self.edit_widgets['business_type'].get_selected_items(),
            'company_password': self.edit_widgets['company_password'].text(),
            'public_info': self.edit_widgets['public_info'].toPlainText(),
                'remarks': self.edit_widgets['remarks'].toPlainText(),
                'proxy_start_date': self.edit_widgets['proxy_start_date'].date().toString('yyyy-MM-dd'),
                'proxy_end_date': self.edit_widgets['proxy_end_date'].date().toString('yyyy-MM-dd')
            }
            
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                # 确保 business_type 列存在
                cursor.execute("PRAGMA table_info(business)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'business_type' not in columns:
                    cursor.execute("ALTER TABLE business ADD COLUMN business_type TEXT")

                cursor.execute('''
                    UPDATE business SET 
                    company_name=?, business_name=?, business_type=?,
                    company_password=?, public_info=?, remarks=?,
                    proxy_start_date=?, proxy_end_date=?
                    WHERE id=?
                ''', (
                    data['company_name'], data['business_name'], data['business_type'],
                    data['company_password'], data['public_info'], data['remarks'],
                    data['proxy_start_date'], data['proxy_end_date'],
                    self.current_biz_id
                ))
                self.db_manager.conn.commit()
                
            # 更新列表显示
            current_item = self.list_widget.currentItem()
            if current_item:
                # 获取旧数据并更新
                item_data = current_item.data(Qt.UserRole)
                item_data.update(data)
                
                current_item.setData(Qt.UserRole, item_data)
                
                # 刷新卡片
                new_card = BusinessCardWidget(item_data)
                current_item.setSizeHint(new_card.sizeHint())
                self.list_widget.setItemWidget(current_item, new_card)
            
            QMessageBox.information(self, "成功", "修改已保存")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


    def _delete_business_item(self, data):
        """删除指定业务记录"""
        biz_id = data.get('id')
        company_name = data.get('company_name', '未命名')
        
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除 "{company_name}" 的业务记录吗?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 软删除
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute(
                        'UPDATE business SET is_deleted = 1, deleted_at = ? WHERE id = ?',
                        (now, biz_id)
                    )
                    self.db_manager.conn.commit()
                
                # 如果删除的是当前选中的，清空详情面板
                if hasattr(self, 'current_biz_id') and self.current_biz_id == biz_id:
                    self.current_biz_id = None
                    self.detail_frame.setEnabled(False)
                    for widget in self.edit_widgets.values():
                        if isinstance(widget, QLineEdit):
                            widget.clear()
                        elif isinstance(widget, QTextEdit):
                            widget.clear()
                        elif isinstance(widget, QCheckBox):
                            widget.setChecked(False)
                            
                # 刷新列表
                self._load_business()
                if hasattr(self.parent(), 'refresh_stats'):
                    self.parent().refresh_stats()
                    
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def _delete_current_business(self):
        """删除当前选中的业务"""
        if not hasattr(self, 'current_biz_id') or not self.current_biz_id:
            return
            
        company_name = self.edit_widgets['company_name'].text()
        
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除 "{company_name}" 的业务记录吗?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute(
                    'UPDATE finance SET business_id = NULL WHERE business_id = ?',
                    (self.current_biz_id,)
                )
                from datetime import datetime
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(
                    'UPDATE business SET is_deleted = 1, deleted_at = ? WHERE id = ?',
                    (now, self.current_biz_id)
                )
                
            # 清空详情面板
            self.detail_frame.setEnabled(False)
            self.current_biz_id = None
            for widget in self.edit_widgets.values():
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QTextEdit):
                    widget.clear()
                    
            # 刷新表格
            self._load_business()
                
        except Exception as e:
            QMessageBox.critical(
                self,
                '删除错误',
                f'删除业务记录失败: {str(e)}'
            )


    def _add_business(self):
        """添加业务记录"""
        dialog = BusinessEditDialog(self.db_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_business()



    def _import_business(self):
        """从Excel文件导入业务数据(增量导入)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择业务数据文件',
            '',
            'Excel文件 (*.xlsx)'
        )
        
        if not file_path:
            return
            
        try:
            # 初始化导入器
            importer = BaseImporterExporter()
            importer._required_columns = ['公司名称', '业务名称']
            importer._column_mapping = {
                '公司名称': 'company_name',
                '业务名称': 'business_name',
                '业务类型': 'business_type',
                '二级业务': 'secondary_business',
                '公司密码': 'company_password',
                '公开信息': 'public_info',
                '备注': 'remarks',
                '代理记账': 'proxy_accounting',
                '工商代办': 'business_agent',
                '代理记账时间段': 'proxy_period',
                '记账周期': 'proxy_period'
            }
            
            # 获取现有数据用于去重
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute('SELECT company_name, business_name FROM business')
                existing_business = [{'company_name': row[0], 'business_name': row[1]} 
                                  for row in cursor.fetchall()]
                importer.cache_existing_data(
                    existing_business,
                    key_columns=['company_name', 'business_name']
                )
            
            # 从Excel导入数据
            imported_data = importer.import_from_excel(
                file_path=file_path,
                sheet_name='业务数据',
                key_columns=['company_name', 'business_name'],
                skip_duplicates=True
            )
            
            if not imported_data:
                QMessageBox.information(self, '导入完成', '没有可导入的数据')
                return
                
            # 准备导入数据
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            records_to_insert = []
            for row in imported_data:
                # 处理代理记账时间段
                proxy_period = row.get('proxy_period', '')
                start_date, end_date = '', ''
                if proxy_period:
                    if '至' in proxy_period:
                        parts = proxy_period.split('至')
                        start_date = parts[0].strip()
                        end_date = parts[1].strip() if len(parts) > 1 else ''
                    else:
                        start_date = proxy_period.strip()
                
                # 处理业务类型
                b_type = row.get('business_type', '')
                if not b_type:
                    if row.get('proxy_accounting'):
                        b_type = '代理记账'
                    elif row.get('business_agent'):
                        b_type = '工商代办'
                
                records_to_insert.append((
                    row.get('company_name', ''),
                    row.get('business_name', ''),
                    b_type,
                    row.get('secondary_business', ''),
                    row.get('company_password', ''),
                    row.get('public_info', ''),
                    row.get('remarks', ''),
                    1 if row.get('proxy_accounting', False) else 0,
                    1 if row.get('business_agent', False) else 0,
                    start_date,
                    end_date,
                    now,
                    'active'
                ))
            
            # 执行批量导入
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.executemany('''
                    INSERT OR IGNORE INTO business (
                        company_name, business_name, business_type, secondary_business,
                        company_password, public_info, remarks,
                        proxy_accounting, business_agent,
                        proxy_start_date, proxy_end_date,
                        create_time, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', records_to_insert)
                
                inserted_count = cursor.rowcount
                total_count = len(imported_data)
                skipped_count = total_count - inserted_count
                
            # 刷新界面和数据
            self._load_business()
            
            # 显示导入结果
            QMessageBox.information(
                self,
                '导入完成',
                f'成功导入 {inserted_count} 条业务记录\n'
                f'跳过 {skipped_count} 条重复记录\n'
                f'共处理 {total_count} 条记录'
            )
            
            # 刷新首页统计数据
            if hasattr(self.parent(), 'refresh_stats'):
                self.parent().refresh_stats()
            
        except ImportExportError as e:
            QMessageBox.critical(self, '导入错误', str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                '导入失败',
                f'导入过程中发生错误:\n{str(e)}\n'
                '请检查文件格式是否正确'
            )

    def _export_business(self):
        """导出业务数据为Excel格式"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '导出业务数据',
            f'业务数据_{datetime.now().strftime("%Y%m%d")}.xlsx',
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
                
                # 先检查数据量
                cursor.execute('SELECT COUNT(*) FROM business')
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    QMessageBox.warning(self, '警告', '业务表中没有数据可导出')
                    return
                    
                # 获取完整的表结构信息
                cursor.execute("PRAGMA table_info(business)")
                table_info = cursor.fetchall()
                all_columns = [col[1] for col in table_info]
                logger.debug(f"Database table structure: {all_columns}")
                
                # 确保查询所有必要字段
                required_columns = [
                    'company_name', 'business_name', 'business_type', 'secondary_business',
                    'company_password', 'public_info', 'remarks',
                    'proxy_accounting', 'business_agent',
                    'proxy_start_date', 'proxy_end_date',
                    'create_time', 'status'
                ]
                
                # 构建查询语句，只包含实际存在的列
                select_columns = [col for col in required_columns if col in all_columns]
                if not select_columns:
                    raise Exception("没有可导出的有效列")
                    
                query = f"SELECT {','.join(select_columns)} FROM business ORDER BY create_time DESC"
                logger.debug(f"Executing query: {query}")
                cursor.execute(query)
                
                rows = cursor.fetchall()
                if not rows:
                    raise Exception("数据库查询返回空结果")
                
                # 转换为字典列表格式，处理NULL值
                data = []
                for row in rows:
                    row_data = {}
                    for idx, col in enumerate(select_columns):
                        # 将None转换为空字符串
                        row_data[col] = '' if row[idx] is None else row[idx]
                    data.append(row_data)
                
                logger.info(f"Retrieved {len(data)} records")
                
                # 验证数据转换
                if len(data) != total_count:
                    raise Exception(f"数据转换不一致: 预期{total_count}条, 实际{len(data)}条")
                
                # 处理数据转换
                export_data = []
                for item in data:
                    # 确保所有字段都有值
                    row = {
                        '公司名称': item.get('company_name', ''),
                        '业务名称': item.get('business_name', ''),
                        '业务类型': item.get('business_type', ''),
                        '二级业务': item.get('secondary_business', ''),
                        '公司密码': item.get('company_password', ''),
                        '公开信息': item.get('public_info', ''),
                        '备注': item.get('remarks', ''),
                        '代理记账': '是' if item.get('proxy_accounting', 0) else '否',
                        '工商代办': '是' if item.get('business_agent', 0) else '否'
                    }
                    
                    # 处理代理记账时间段
                    start = item.get('proxy_start_date', '')
                    end = item.get('proxy_end_date', '')
                    if start and end:
                        row['记账周期'] = f"{start} 至 {end}"
                    elif start:
                        row['记账周期'] = start
                    elif end:
                        row['记账周期'] = f"至 {end}"
                    else:
                        row['记账周期'] = ""
                    
                    export_data.append(row)
                
                logger.info(f"Preparing to export {len(export_data)} records")
                
                # 使用BaseImporterExporter导出
                exporter = BaseImporterExporter()
                if not hasattr(exporter, 'export_to_excel'):
                    raise Exception("BaseImporterExporter缺少export_to_excel方法")
                    
                # 定义表头顺序
                headers = [
                    '公司名称', '业务名称', '业务类型', '二级业务',
                    '公司密码', '公开信息', '备注',
                    '代理记账', '工商代办', '记账周期'
                ]
                
                # 验证数据
                for i, item in enumerate(export_data):
                    if not item['公司名称'] or not item['业务名称']:
                        logger.warning(f"Warning: Record {i+1} missing company name or business name")
                
                exporter.export_to_excel(
                    data=export_data,
                    file_path=file_path,
                    sheet_name='业务数据',
                    headers=headers
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
                    f'业务数据已成功导出到:\n{file_path}\n'
                    f'共导出 {len(data)} 条记录\n'
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

    def search_and_select(self, query):
        """外部调用搜索并选中第一条"""
        self.pending_select_query = query
        self.search_input.setText(query)
        # textChanged triggers _search_business -> _load_business

    def _search_business(self):
        """搜索业务记录"""
        self.page = 1
        self._load_business()

    def _populate_list(self, rows):
        """填充列表数据"""
        self.list_widget.clear()
        
        for row_data in rows:
            # Helper to safely get value
            def get_val(idx):
                return row_data[idx] if idx < len(row_data) and row_data[idx] is not None else ""
            
            # 注意: 索引必须与查询语句对应
            # 0:id, 1:company_name, 2:business_name, 3:business_type, 4:secondary_business,
            # 5:company_password, 6:public_info, 7:remarks,
            # 8:deal_business, 9:proxy_start_date, 10:proxy_end_date,
            # 11:proxy_accounting, 12:business_agent, 13:other_business
            
            data = {
                'id': row_data[0],
                'company_name': get_val(1),
                'business_name': get_val(2),
                'business_type': get_val(3),
                'secondary_business': get_val(4),
                'company_password': get_val(5),
                'public_info': get_val(6),
                'remarks': get_val(7),
                'deal_business': get_val(8),
                'proxy_start_date': get_val(9),
                'proxy_end_date': get_val(10),
                'proxy_accounting': bool(row_data[11]) if 11 < len(row_data) else False,
                'business_agent': bool(row_data[12]) if 12 < len(row_data) else False,
                'other_business': get_val(13)
            }
            
            # Logic for deal_business if empty
            if not data['deal_business']:
                deal_parts = []
                if data['proxy_accounting']: deal_parts.append("代理记账")
                if data['business_agent']: deal_parts.append("工商代办")
                if data['other_business']: deal_parts.append(data['other_business'])
                data['deal_business'] = " ".join(deal_parts)

            # Create Card
            card = BusinessCardWidget(data)
            card.set_callback('delete', lambda d=data: self._delete_business_item(d))
            
            # Create Item
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(card.sizeHint())
            item.setData(Qt.UserRole, data) # Store full data in item
            
            self.list_widget.setItemWidget(item, card)

    def _on_list_item_clicked(self, item):
        """列表项点击事件"""
        data = item.data(Qt.UserRole)
        if not data:
            return
            
        self.current_biz_id = data['id']
        self.detail_frame.setEnabled(True)
        
        # 填充详情面板
        self.edit_widgets['company_name'].setText(str(data['company_name']))
        self.edit_widgets['business_name'].setText(str(data.get('business_name', '')))
        
        # 业务类型处理
        b_type = str(data.get('business_type', ''))
        
        # 兼容旧数据
        if not b_type or b_type == '服务业务':
            if data.get('proxy_accounting'):
                b_type = '代理记账'
            elif data.get('business_agent'):
                b_type = '工商代办'
            elif data.get('other_business'):
                b_type = '其他业务'
        
        self.edit_widgets['business_type'].refresh()
        self.edit_widgets['business_type'].set_selected_items(b_type)
        
        self.edit_widgets['company_password'].setText(str(data['company_password']))
        self.edit_widgets['public_info'].setPlainText(str(data['public_info']))
        self.edit_widgets['remarks'].setPlainText(str(data['remarks']))
        
        # Date fields
        def parse_date(d):
            if not d: return QDate.currentDate()
            try: return QDate.fromString(str(d), 'yyyy-MM-dd')
            except: return QDate.currentDate()
            
        self.edit_widgets['proxy_start_date'].setDate(parse_date(data['proxy_start_date']))
        self.edit_widgets['proxy_end_date'].setDate(parse_date(data['proxy_end_date']))

    def _check_schema(self):
        """Ensure necessary columns exist"""
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("PRAGMA table_info(business)")
                columns = [col[1] for col in cursor.fetchall()]
                
                required_columns = {
                    'business_type': 'TEXT',
                    'deal_business': 'TEXT',
                    'proxy_accounting_date': 'TEXT',
                    'proxy_accounting': 'INTEGER DEFAULT 0',
                    'business_agent': 'INTEGER DEFAULT 0',
                    'other_business': 'TEXT',
                    'proxy_start_date': 'TEXT',
                    'proxy_end_date': 'TEXT',
                    'status': 'TEXT'
                }
                
                for col_name, col_type in required_columns.items():
                    if col_name not in columns:
                        try:
                            cursor.execute(f'ALTER TABLE business ADD COLUMN {col_name} {col_type}')
                            logger.info(f"Added column: {col_name} ({col_type})")
                        except sqlite3.Error as e:
                            logger.error(f"Failed to add column {col_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Schema check failed: {e}")

    def _fetch_data_worker(self, search_text, sort_option, limit, offset):
        """Worker function to fetch data in background"""
        try:
            conn = self.db_manager.create_new_connection()
            cursor = conn.cursor()
            
            where_clauses = ["is_deleted = 0"]
            params = []
            
            if search_text:
                where_clauses.append("(company_name LIKE ? OR business_name LIKE ?)")
                params.extend([f'%{search_text}%', f'%{search_text}%'])
            
            where_sql = " AND ".join(where_clauses)
            
            # Count total
            count_sql = f"SELECT COUNT(*) FROM business WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # Determine Order
            order_by = "create_time DESC"
            if sort_option == '创建时间 (新→旧)':
                order_by = "create_time DESC"
            elif sort_option == '创建时间 (旧→新)':
                order_by = "create_time ASC"
            elif sort_option == '公司名称 (A→Z)':
                order_by = "company_name ASC"
            elif sort_option == '公司名称 (Z→A)':
                order_by = "company_name DESC"
            
            # Fetch data
            data_sql = f"""
                SELECT 
                    id, company_name, business_name, business_type, secondary_business,
                    company_password, public_info, remarks,
                    deal_business, proxy_start_date, proxy_end_date,
                    proxy_accounting, business_agent, other_business
                FROM business
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, params + [limit, offset])
            rows = cursor.fetchall()
            
            conn.close()
            return rows, total
        except Exception as e:
            logger.error(f"Fetch data error: {e}")
            return [], 0

    def _load_business(self):
        """从数据库异步加载业务数据"""
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.list_widget.clear()
        
        search_text = self.search_input.text().strip()
        sort_option = self.sort_combo.currentText()
        offset = (self.page - 1) * self.page_size
        
        worker = Worker(self._fetch_data_worker, search_text, sort_option, self.page_size, offset)
        worker.signals.result.connect(self._on_load_success)
        worker.signals.error.connect(self._on_load_error)
        self.threadpool.start(worker)

    def _on_sort_changed(self):
        self.page = 1
        self._load_business()

    def _jump_to_page(self):
        text = self.jump_input.text().strip()
        if not text:
            return
        try:
            page = int(text)
            if 1 <= page <= self.total_pages:
                self.page = page
                self._load_business()
                self.jump_input.clear()
            else:
                QMessageBox.warning(self, "提示", f"请输入 1 到 {self.total_pages} 之间的页码")
                self.jump_input.selectAll()
                self.jump_input.setFocus()
        except ValueError:
            pass

    def _on_load_success(self, result):
        rows, total = result
        self.total_records = total
        self.total_pages = math.ceil(total / self.page_size) if total > 0 else 1
        
        if self.page > self.total_pages:
            self.page = self.total_pages
            
        self._populate_list(rows)
        self._update_pagination_ui()
        
        # 处理待处理的选中请求
        if self.pending_select_query:
            query = self.pending_select_query
            self.pending_select_query = None # 清除标志
            
            # 尝试查找匹配项
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                data = item.data(Qt.UserRole)
                if data:
                    company = data.get('company_name', '')
                    business = data.get('business_name', '')
                    # 如果查询词包含在公司名或业务名中，选中第一条
                    if query in company or query in business:
                        self.list_widget.setCurrentItem(item)
                        self._on_list_item_clicked(item)
                        self.list_widget.scrollToItem(item)
                        break

    def _on_load_error(self, error):
        QMessageBox.warning(self, "加载失败", f"数据加载出错: {error[1]}")
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

    def _update_pagination_ui(self):
        self.page_label.setText(f"第 {self.page} / {self.total_pages} 页")
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.total_pages)

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_business()

    def _next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self._load_business()
    
    # OLD _load_business removed
    
    def _select_all_business(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'set_checked'):
                card.set_checked(True)
    
    def _invert_selection_business(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'is_checked'):
                card.set_checked(not card.is_checked())
    
    def _clear_selection_business(self):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'set_checked'):
                card.set_checked(False)
    
    def _delete_selected_business(self):
        ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            card = self.list_widget.itemWidget(item)
            if card and hasattr(card, 'is_checked') and card.is_checked():
                data = item.data(Qt.UserRole)
                if data and 'id' in data:
                    ids.append(int(data['id']))
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除选中的 {len(ids)} 条业务记录吗?',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                from datetime import datetime
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                for bid in ids:
                    cursor.execute('UPDATE finance SET business_id = NULL WHERE business_id = ?', (bid,))
                    cursor.execute('UPDATE business SET is_deleted = 1, deleted_at = ? WHERE id = ?', (now, bid))
            self._load_business()
            self.detail_frame.setEnabled(False)
            self.current_biz_id = None
        except Exception as e:
            QMessageBox.critical(self, '删除错误', f'删除业务记录失败: {str(e)}')

