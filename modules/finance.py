from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem,
                             QLineEdit, QTextEdit, QFormLayout, QDialog, QMessageBox, 
                             QHeaderView, QDateEdit, QDoubleSpinBox, QComboBox,
                             QScrollArea, QFrame, QAbstractItemView, QCheckBox, QWidget,
                             QGridLayout, QMenu, QGroupBox, QButtonGroup, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QSize
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PyQt5.QtGui import QPainter, QFont, QColor, QIntValidator
import sqlite3
from datetime import datetime
from core.logger import logger
from core.async_utils import Worker, QThreadPool
from modules.common_widgets import CustomerSelectionCombo, SingleSelectionWidget, ModernDateEdit
from modules.base_card import BaseCardWidget
from core.constants import FINANCE_TAG_COLORS

class FinanceCardWidget(BaseCardWidget):
    """财务卡片控件"""
    def __init__(self, data, parent=None):
        super().__init__(data, parent)
        self.setProperty("class", "card finance-card")
        self.setFixedSize(360, 250)
        

        
    def _init_ui(self):
        # 设置提示信息（备注）
        notes = self.data.get('notes', '')
        if notes:
            self.setToolTip(f"备注: {notes}")
            
        self.setProperty("class", "finance-card")
        
        # Use existing main_layout from BaseCardWidget
        main_layout = self.main_layout
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)
        
        # 1. 顶部：项目名称 + 日期
        top_layout = QHBoxLayout()
        
        top_layout.addWidget(self.create_checkbox())
        
        # 项目名称
        company_label = QLabel(self.data.get('company_name', ''))
        company_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        company_label.setWordWrap(True)
        top_layout.addWidget(company_label, 1)
        
        # 日期
        date_label = QLabel(self.data.get('due_date', ''))
        date_label.setProperty("class", "info-text")
        date_label.setStyleSheet("font-size: 11px;")
        top_layout.addWidget(date_label)
        
        main_layout.addLayout(top_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.NoFrame)
        line.setFixedHeight(1)
        line.setProperty("class", "separator")
        main_layout.addWidget(line)
        
        # 2. 中部：核心财务数据 (3列)
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(5)
        
        # 金额
        metrics_layout.addWidget(QLabel("总金额:"), 0, 0)
        amount_val = QLabel(f"¥{self.data.get('amount', 0):.2f}")
        amount_val.setStyleSheet("font-weight: bold; font-size: 13px;")
        metrics_layout.addWidget(amount_val, 0, 1)
        
        # 成本
        metrics_layout.addWidget(QLabel("成本:"), 1, 0)
        cost_val = QLabel(f"¥{self.data.get('cost', 0):.2f}")
        metrics_layout.addWidget(cost_val, 1, 1)
        
        # 利润
        metrics_layout.addWidget(QLabel("利润:"), 2, 0)
        profit = self.data.get('profit', 0)
        profit_val = QLabel(f"¥{profit:.2f}")
        profit_color = "#67c23a" if profit >= 0 else "#f56c6c"
        profit_val.setStyleSheet(f"color: {profit_color}; font-weight: bold; font-size: 13px;")
        metrics_layout.addWidget(profit_val, 2, 1)
        
        main_layout.addLayout(metrics_layout)
        
        # 分隔线2
        line2 = QFrame()
        line2.setFrameShape(QFrame.NoFrame)
        line2.setFixedHeight(1)
        line2.setProperty("class", "separator")
        main_layout.addWidget(line2)
        
        # 3. 新增字段展示 (2行2列)
        tags_layout = QGridLayout()
        tags_layout.setSpacing(4)
        
        def create_tag(label, text, color_cond=None):
            container = QWidget()
            l = QHBoxLayout(container)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(4)
            
            # Label
            # lbl = QLabel(label)
            # lbl.setStyleSheet("color: #909399; font-size: 11px;")
            # l.addWidget(lbl)
            
            # Value
            val = QLabel(text if text else "—")
            style = "background: #f4f4f5; color: #909399; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            
            if text and color_cond:
                if text in color_cond.get('success', []):
                    style = "background: #f0f9eb; color: #67c23a; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
                elif text in color_cond.get('warning', []):
                    style = "background: #fdf6ec; color: #e6a23c; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
                elif text in color_cond.get('danger', []):
                    style = "background: #fef0f0; color: #f56c6c; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            
            val.setStyleSheet(style)
            l.addWidget(val)
            l.addStretch()
            return container

        # Payment
        pay_method = self.data.get('payment_method')
        tags_layout.addWidget(create_tag("支付:", pay_method), 0, 0)
        
        # Contract
        contract_status = self.data.get('contract_status')
        tags_layout.addWidget(create_tag("合同:", contract_status, FINANCE_TAG_COLORS['contract']), 0, 1)
        
        # Project
        proj_status = self.data.get('project_status')
        tags_layout.addWidget(create_tag("进度:", proj_status, FINANCE_TAG_COLORS['project']), 1, 0)
        
        # Invoice
        inv_status = self.data.get('invoice_status')
        tags_layout.addWidget(create_tag("开票:", inv_status, FINANCE_TAG_COLORS['invoice']), 1, 1)
        
        main_layout.addLayout(tags_layout)
        
        main_layout.addStretch()
        
        # 3. 底部：待收款预警条
        pending_amount = self.data.get('pending_amount', 0)
        pending_date = self.data.get('pending_date', '')
        
        status_frame = QFrame()
        status_frame.setObjectName("finance-status-bar")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        status_text = ""
        status_style = ""
        border_color = "#ebeef5" # 默认边框
        status_prop = "ok"
        
        # 深色模式背景适配
        from PyQt5.QtCore import QSettings
        is_dark = (QSettings("CustomerManagement", "Settings").value("theme", "浅色") == "深色")
        if pending_amount <= 0:
            # 已结清
            status_text = "✅ 款项已结清"
            status_style = "color: #67c23a; font-size: 12px; font-weight: bold;"
            status_prop = "ok"
        else:
            # 有待收款
            today = QDate.currentDate().toString('yyyy-MM-dd')
            is_overdue = pending_date and pending_date < today
            
            if is_overdue:
                # 已逾期
                status_text = f"🚨 逾期: ¥{pending_amount:.2f}"
                if pending_date:
                    status_text += f" ({pending_date})"
                status_style = "color: #f56c6c; font-size: 12px; font-weight: bold;"
                status_prop = "overdue"
                border_color = "#f56c6c" # 卡片边框变红
            else:
                # 待收款
                status_text = f"⏳ 待收: ¥{pending_amount:.2f}"
                if pending_date:
                    status_text += f" ({pending_date})"
                status_style = "color: #e6a23c; font-size: 12px; font-weight: bold;"
                status_prop = "pending"
                border_color = "#e6a23c" # 卡片边框变橙
        
        # 应用状态动态属性以匹配QSS
        status_frame.setProperty("status", status_prop)
        status_frame.style().unpolish(status_frame)
        status_frame.style().polish(status_frame)
        
        # 更新卡片边框颜色
        if border_color != "#ebeef5":
            self.setStyleSheet(f"""
                QFrame[class="finance-card"] {{
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
                QFrame[class="finance-card"]:hover {{
                    border: 1px solid {border_color};
                }}
                QLabel {{ border: none; background: transparent; }}
            """)
            
        status_label = QLabel(status_text)
        status_label.setWordWrap(True)
        status_label.setStyleSheet(status_style)
        status_layout.addWidget(status_label, 1)  # Give it stretch factor
        status_layout.addStretch(0)  # Remove extra stretch or keep it small
        
        # 操作按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setProperty("class", "primary small-btn")
        edit_btn.clicked.connect(lambda: self.callbacks.get('edit', lambda: None)())
        status_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setProperty("class", "danger small-btn")
        delete_btn.clicked.connect(lambda: self.callbacks.get('delete', lambda: None)())
        status_layout.addWidget(delete_btn)
        
        main_layout.addWidget(status_frame)
        


class FinanceEditDialog(QDialog):
    """财务记录编辑对话框"""
    def __init__(self, db_manager, finance_data=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.finance_data = finance_data
        self.setWindowTitle('新增财务记录' if not finance_data else '编辑财务记录')
        self.resize(650, 800)  # Use resize instead of setFixedSize
        self._init_ui()
        if self.finance_data:
            self._load_data()
        else:
            self._init_defaults()

    def _init_ui(self):
        # Main layout for the dialog
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        # Content Widget inside Scroll Area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. 项目信息
        project_group = QGroupBox("项目信息")
        project_layout = QGridLayout()
        project_layout.setSpacing(15)
        
        project_layout.addWidget(QLabel('项目名称*:'), 0, 0)
        self.project_name = CustomerSelectionCombo(self.db_manager)
        project_layout.addWidget(self.project_name, 0, 1, 1, 3)
        
        project_layout.addWidget(QLabel('项目日期:'), 1, 0)
        self.due_date = ModernDateEdit()
        self.due_date.setDate(QDate.currentDate())
        self.due_date.setDisplayFormat("yyyy-MM-dd")
        project_layout.addWidget(self.due_date, 1, 1)
        
        project_layout.addWidget(QLabel('合同状态:'), 2, 0)
        self.contract_status = SingleSelectionWidget(self.db_manager, 'finance_contract_status', 'name', multi_select=True)
        project_layout.addWidget(self.contract_status, 2, 1)
        
        project_layout.addWidget(QLabel('项目进度:'), 2, 2)
        self.project_status = SingleSelectionWidget(self.db_manager, 'finance_project_status', 'name', multi_select=True)
        project_layout.addWidget(self.project_status, 2, 3)
        
        project_group.setLayout(project_layout)
        layout.addWidget(project_group)

        # 2. 财务数据
        finance_group = QGroupBox("财务数据")
        finance_layout = QGridLayout()
        finance_layout.setSpacing(15)
        
        finance_layout.addWidget(QLabel('收款金额:'), 0, 0)
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 9999999)
        self.amount.setPrefix('¥ ')
        self.amount.setDecimals(2)
        finance_layout.addWidget(self.amount, 0, 1)
        
        finance_layout.addWidget(QLabel('成本支出:'), 0, 2)
        self.cost = QDoubleSpinBox()
        self.cost.setRange(0, 9999999)
        self.cost.setPrefix('¥ ')
        self.cost.setDecimals(2)
        finance_layout.addWidget(self.cost, 0, 3)
        
        finance_layout.addWidget(QLabel('利润(自动):'), 1, 0)
        self.profit_label = QLineEdit('¥ 0.00')
        self.profit_label.setReadOnly(True)
        self.profit_label.setStyleSheet('font-weight: bold; color: #606266; background: #f5f7fa;')
        finance_layout.addWidget(self.profit_label, 1, 1)
        
        finance_layout.addWidget(QLabel('支付方式:'), 1, 2)
        self.payment_method = SingleSelectionWidget(self.db_manager, 'finance_payment_methods', 'name', multi_select=True)
        finance_layout.addWidget(self.payment_method, 1, 3)
        
        finance_layout.addWidget(QLabel('开票状态:'), 2, 0)
        self.invoice_status = SingleSelectionWidget(self.db_manager, 'finance_invoice_status', 'name', multi_select=True)
        finance_layout.addWidget(self.invoice_status, 2, 1)

        finance_group.setLayout(finance_layout)
        layout.addWidget(finance_group)
        
        # 3. 待收管理
        pending_group = QGroupBox("待收管理")
        pending_layout = QGridLayout()
        pending_layout.setSpacing(15)
        
        pending_layout.addWidget(QLabel('待收金额:'), 0, 0)
        pending_box_layout = QHBoxLayout()
        self.pending_amount = QDoubleSpinBox()
        self.pending_amount.setRange(0, 9999999)
        self.pending_amount.setPrefix('¥ ')
        self.pending_amount.setDecimals(2)
        
        self.settle_btn = QPushButton("一键结清")
        self.settle_btn.setCursor(Qt.PointingHandCursor)
        self.settle_btn.setProperty("class", "success small-btn")
        self.settle_btn.clicked.connect(lambda: self.pending_amount.setValue(0))
        
        pending_box_layout.addWidget(self.pending_amount)
        pending_box_layout.addWidget(self.settle_btn)
        pending_layout.addLayout(pending_box_layout, 0, 1)
        
        pending_layout.addWidget(QLabel('待收日期:'), 0, 2)
        self.pending_date = ModernDateEdit()
        self.pending_date.setDate(QDate.currentDate().addDays(30))
        self.pending_date.setDisplayFormat("yyyy-MM-dd")
        self.pending_date.setEnabled(False)
        pending_layout.addWidget(self.pending_date, 0, 3)
        
        pending_group.setLayout(pending_layout)
        layout.addWidget(pending_group)
        
        # 4. 备注
        notes_group = QGroupBox("备注")
        notes_layout = QVBoxLayout()
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("填写备注信息...")
        self.notes.setMinimumHeight(240)
        notes_layout.addWidget(self.notes)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        layout.addStretch()
        
        # Set scroll widget
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # 按钮 (Fixed at bottom)
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(20, 10, 20, 20)
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
        
        main_layout.addWidget(btn_container)
        
        # 信号连接
        self.amount.valueChanged.connect(self._update_profit)
        self.cost.valueChanged.connect(self._update_profit)
        self.pending_amount.valueChanged.connect(lambda v: self.pending_date.setEnabled(v > 0))

    def _update_profit(self):
        profit = self.amount.value() - self.cost.value()
        self.profit_label.setText(f'¥ {profit:.2f}')

    def _init_defaults(self):
        self.project_name.setCurrentIndex(-1)
        self.project_name.lineEdit().clear()
        self.payment_method.set_selected('对公账户')
        self.contract_status.set_selected('未签订')
        self.project_status.set_selected('未完结')
        self.invoice_status.set_selected('未开票')

    def _load_data(self):
        d = self.finance_data
        if isinstance(d, dict):
             self.project_name.setCurrentText(d.get('company_name', ''))
             self.amount.setValue(float(d.get('amount', 0)))
             self.cost.setValue(float(d.get('cost', 0)))
             self.due_date.setDate(QDate.fromString(d.get('due_date', ''), 'yyyy-MM-dd'))
             self.notes.setText(d.get('notes', ''))
             self.pending_amount.setValue(float(d.get('pending_amount', 0)))
             p_date_str = d.get('pending_date', '')
             if p_date_str:
                 self.pending_date.setDate(QDate.fromString(p_date_str, 'yyyy-MM-dd'))
             
             self.payment_method.set_selected(d.get('payment_method', ''))
             self.contract_status.set_selected(d.get('contract_status', ''))
             self.project_status.set_selected(d.get('project_status', ''))
             self.invoice_status.set_selected(d.get('invoice_status', ''))
        else:
             # Legacy support
             self.project_name.setCurrentText(d[1])
             self.amount.setValue(float(d[2]))
             self.cost.setValue(float(d[3]))
             self.due_date.setDate(QDate.fromString(d[5], 'yyyy-MM-dd'))
             self.notes.setText(d[6])

    def _save(self):
        project_name = self.project_name.currentText().strip()
        amount = self.amount.value()
        cost = self.cost.value()
        due_date = self.due_date.date().toString('yyyy-MM-dd')
        
        if not all([project_name, amount >= 0, due_date]):
            QMessageBox.warning(self, '错误', '请填写所有必填字段')
            return
            
        profit = amount - cost
        notes = self.notes.toPlainText()
        pending_amount = self.pending_amount.value()
        pending_date = self.pending_date.date().toString('yyyy-MM-dd') if pending_amount > 0 else ''
        
        # Helper to get comma-separated string from widget
        def get_multi_val(widget):
            val = widget.get_selected()
            if isinstance(val, list):
                return ",".join(val)
            return val or ""

        payment_method = get_multi_val(self.payment_method)
        contract_status = get_multi_val(self.contract_status)
        project_status = get_multi_val(self.project_status)
        invoice_status = get_multi_val(self.invoice_status)
        
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                
                fin_id = None
                if isinstance(self.finance_data, dict):
                    fin_id = self.finance_data.get('id')
                elif isinstance(self.finance_data, (tuple, list)):
                     fin_id = self.finance_data[0]

                if fin_id:
                    cursor.execute('''
                        UPDATE finance SET 
                            company_name = ?, amount = ?, cost = ?, profit = ?, 
                            due_date = ?, notes = ?, pending_amount = ?, pending_date = ?,
                            payment_method = ?, contract_status = ?, project_status = ?, invoice_status = ?
                        WHERE id = ?
                    ''', (project_name, amount, cost, profit, due_date, notes, pending_amount, pending_date, 
                          payment_method, contract_status, project_status, invoice_status, fin_id))
                else:
                    cursor.execute('''
                        INSERT INTO finance (
                            company_name, amount, cost, profit, due_date, notes, pending_amount, pending_date,
                            payment_method, contract_status, project_status, invoice_status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (project_name, amount, cost, profit, due_date, notes, pending_amount, pending_date,
                          payment_method, contract_status, project_status, invoice_status))
            
            self.accept()
        
        except sqlite3.Error as e:
            QMessageBox.warning(self, '错误', f'保存失败: {str(e)}')

class FinanceFilterDialog(QDialog):
    """财务数据筛选对话框"""
    def __init__(self, db_manager, parent=None, title='筛选选项', confirm_text='确定', hint_text=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle(title)
        self.confirm_text = confirm_text
        self.hint_text = hint_text or "提示: 项目名称留空且不勾选日期筛选，将统计所有数据"
        self.setFixedSize(400, 320)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 筛选条件分组
        filter_group = QGroupBox("筛选条件")
        filter_layout = QFormLayout()
        filter_layout.setSpacing(10)
        
        # 1. 公司/项目筛选 (直接启用，不使用Checkbox)
        self.company_combo = CustomerSelectionCombo(self.db_manager)
        self.company_combo.setPlaceholderText("请输入项目名称...")
        self.company_combo.setCurrentIndex(-1)  # 默认不选中任何项
        filter_layout.addRow("项目名称:", self.company_combo)
        
        # 2. 日期范围筛选 (使用Checkbox控制)
        self.date_check = QCheckBox("启用日期筛选")
        date_layout = QHBoxLayout()
        
        # 默认上个月到今天
        today = QDate.currentDate()
        self.start_date = ModernDateEdit(today.addMonths(-1))
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        
        self.end_date = ModernDateEdit(today)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("至"))
        date_layout.addWidget(self.end_date)
        
        self.start_date.setEnabled(False)
        self.end_date.setEnabled(False)
        self.date_check.toggled.connect(self.start_date.setEnabled)
        self.date_check.toggled.connect(self.end_date.setEnabled)
        
        # 将Checkbox和日期控件分行显示，避免布局混乱
        filter_layout.addRow(self.date_check)
        filter_layout.addRow("日期范围:", date_layout)
        
        filter_group.setLayout(filter_layout)
        
        layout.addWidget(filter_group)
        
        # 提示信息
        hint_label = QLabel(self.hint_text)
        hint_label.setStyleSheet("color: #909399; font-size: 12px;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFixedSize(80, 32)
        
        export_btn = QPushButton(self.confirm_text)
        export_btn.setProperty("class", "primary")
        export_btn.clicked.connect(self.accept)
        export_btn.setFixedSize(80, 32)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(export_btn)
        
        layout.addLayout(btn_layout)
        
    def get_filters(self):
        """获取筛选条件"""
        filters = {}
        
        # 直接获取输入框内容
        company = self.company_combo.currentText().strip()
        if company:
            filters['company'] = company
                
        if self.date_check.isChecked():
            filters['start_date'] = self.start_date.date().toString('yyyy-MM-dd')
            filters['end_date'] = self.end_date.date().toString('yyyy-MM-dd')
            
        return filters

class FinanceStatsWindow(QDialog):
    """财务统计窗口"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle('财务统计')
        self.resize(1000, 700) # Increased size for better view
        self._init_ui()
        self._update_chart() # Load initial data

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. 顶部筛选栏
        filter_frame = QFrame()
        filter_frame.setProperty("class", "card")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(15)

        # 公司筛选
        filter_layout.addWidget(QLabel("项目名称:"))
        self.company_combo = CustomerSelectionCombo(self.db_manager)
        self.company_combo.setPlaceholderText("全部项目")
        self.company_combo.setCurrentIndex(-1)
        self.company_combo.setFixedWidth(200)
        self.company_combo.currentIndexChanged.connect(self._update_chart)
        filter_layout.addWidget(self.company_combo)

        # 日期范围
        filter_layout.addWidget(QLabel("日期范围:"))
        self.start_date = ModernDateEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-12)) # Default last 12 months
        self.start_date.dateChanged.connect(self._update_chart)
        
        self.end_date = ModernDateEdit(QDate.currentDate())
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.dateChanged.connect(self._update_chart)

        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("-"))
        filter_layout.addWidget(self.end_date)

        # 快速筛选按钮
        btn_group = QHBoxLayout()
        
        self.btn_this_month = QPushButton("本月")
        self.btn_this_month.setCheckable(True)
        self.btn_this_month.clicked.connect(self._filter_this_month)
        
        self.btn_last_year = QPushButton("近一年")
        self.btn_last_year.setCheckable(True)
        self.btn_last_year.setChecked(True) # Default
        self.btn_last_year.clicked.connect(self._filter_last_year)
        
        self.btn_all = QPushButton("全部")
        self.btn_all.setCheckable(True)
        self.btn_all.clicked.connect(self._filter_all)

        # Exclusive buttons logic managed manually or via QButtonGroup
        self.filter_btn_group = QButtonGroup(self)
        self.filter_btn_group.addButton(self.btn_this_month)
        self.filter_btn_group.addButton(self.btn_last_year)
        self.filter_btn_group.addButton(self.btn_all)

        btn_group.addWidget(self.btn_this_month)
        btn_group.addWidget(self.btn_last_year)
        btn_group.addWidget(self.btn_all)
        
        filter_layout.addLayout(btn_group)
        filter_layout.addStretch()

        main_layout.addWidget(filter_frame)

        # 2. 图表区域
        chart_container = QFrame()
        chart_container.setProperty("class", "card")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(10, 10, 10, 10)
        
        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.setBackgroundVisible(False)
        self.chart.setPlotAreaBackgroundVisible(False)
        self.chart.setTitle("月度财务统计")
        self.chart.setTitleFont(QFont("Microsoft YaHei", 12, QFont.Bold))

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        chart_layout.addWidget(self.chart_view)
        main_layout.addWidget(chart_container)

    def _filter_this_month(self):
        today = QDate.currentDate()
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        self.start_date.setDate(QDate(today.year(), today.month(), 1))
        self.end_date.setDate(QDate(today.year(), today.month(), today.daysInMonth()))
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        self._update_chart()

    def _filter_last_year(self):
        today = QDate.currentDate()
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        self.start_date.setDate(today.addMonths(-11)) # Past 12 months including current
        self.end_date.setDate(today)
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        self._update_chart()

    def _filter_all(self):
        # Set a wide range
        self.start_date.blockSignals(True)
        self.end_date.blockSignals(True)
        self.start_date.setDate(QDate(2000, 1, 1))
        self.end_date.setDate(QDate.currentDate())
        self.start_date.blockSignals(False)
        self.end_date.blockSignals(False)
        self._update_chart()

    def _update_chart(self):
        # Gather filters
        filters = {}
        company = self.company_combo.currentText().strip()
        if company:
            filters['company'] = company
        
        # Check which button is active to decide if date filter applies
        # Actually, always apply date filter from the date edits. 
        # The buttons just quick-set the date edits.
        filters['start_date'] = self.start_date.date().toString('yyyy-MM-dd')
        filters['end_date'] = self.end_date.date().toString('yyyy-MM-dd')

        monthly_stats = self._get_monthly_stats(filters)
        
        # Clear chart
        self.chart.removeAllSeries()
        for axis in self.chart.axes():
            self.chart.removeAxis(axis)

        if not monthly_stats:
             # Handle empty data?
             return

        series = QBarSeries()
        income_set = QBarSet('收入')
        expense_set = QBarSet('支出')
        profit_set = QBarSet('利润')
        
        categories = []
        
        # Sort by month
        sorted_months = sorted(monthly_stats.keys())
        for month in sorted_months:
            stats = monthly_stats[month]
            categories.append(month)
            income_set.append(stats['income'])
            expense_set.append(stats['expense'])
            profit_set.append(stats['profit'])
            
        series.append(income_set)
        series.append(expense_set)
        series.append(profit_set)
        self.chart.addSeries(series)
        
        axisX = QBarCategoryAxis()
        axisX.append(categories)
        axis_font = QFont()
        axis_font.setPointSize(9)
        axisX.setLabelsFont(axis_font)
        self.chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)
        
        axisY = QValueAxis()
        axisY.setLabelFormat('%.0f')
        axisY.setTitleText('金额（元）')
        axisY.setLabelsFont(axis_font)
        self.chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)
        
        legend_font = QFont()
        legend_font.setPointSize(9)
        self.chart.legend().setFont(legend_font)
        self.chart.legend().setAlignment(Qt.AlignTop)

    def _get_monthly_stats(self, filters=None):
        """获取月度财务统计数据 (Copied logic to be self-contained)"""
        monthly_stats = {}
        filters = filters or {}
        
        with self.db_manager.conn:
            cursor = self.db_manager.conn.cursor()
            
            query = '''
                SELECT strftime('%Y-%m', due_date) as month,
                       SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                       SUM(CASE WHEN cost > 0 THEN cost ELSE 0 END) as expense,
                       SUM(profit) as profit
                FROM finance
                WHERE is_deleted = 0
            '''
            params = []
            
            if 'company' in filters:
                query += " AND company_name LIKE ?"
                params.append(f"%{filters['company']}%")
                
            if 'start_date' in filters:
                query += " AND due_date >= ?"
                params.append(filters['start_date'])
                
            if 'end_date' in filters:
                query += " AND due_date <= ?"
                params.append(filters['end_date'])
                
            query += '''
                GROUP BY month
                ORDER BY month
            '''
            
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                month, income, expense, profit = row
                monthly_stats[month] = {
                    'income': income or 0,
                    'expense': expense or 0,
                    'profit': profit or 0
                }
                
        return monthly_stats

class FinanceWindow(QWidget):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # Pagination state
        self.page = 1
        self.page_size = 20
        self.total_pages = 0
        self.total_count = 0
        self.pending_select_query = None
        self.threadpool = QThreadPool()
        
        self._check_schema()
        self._init_default_options()
        self._init_ui()
        self._load_finance()
        # self._apply_filters() # Removed as _load_finance is now async and handles filtering
        
    def _init_default_options(self):
        """初始化新字段的默认选项"""
        defaults = {
            'finance_payment_methods': ['对公账户', '微信', '支付宝'],
            'finance_contract_status': ['已签订', '未签订'],
            'finance_project_status': ['已完结', '未完结', '已交接', '未交接'],
            'finance_invoice_status': ['已开票', '未开票']
        }
        
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                for table, items in defaults.items():
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    if cursor.fetchone()[0] == 0:
                        for item in items:
                            cursor.execute(f"INSERT OR IGNORE INTO {table} (name) VALUES (?)", (item,))
            self.db_manager.conn.commit()
        except Exception as e:
            logger.error(f"Failed to init default options: {e}")

    def _check_schema(self):
        """检查并更新数据库结构"""
        try:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute("PRAGMA table_info(finance)")
                columns = [info[1] for info in cursor.fetchall()]
                
                new_columns = [
                    'payment_method', 'contract_status', 
                    'project_status', 'invoice_status'
                ]
                
                for col in new_columns:
                    if col not in columns:
                        cursor.execute(f"ALTER TABLE finance ADD COLUMN {col} TEXT")
        except Exception as e:
            logger.error(f"Schema check failed: {e}")

    def search_and_select(self, query):
        """外部调用搜索并选中第一条"""
        self.pending_select_query = query
        # 重置所有筛选条件以确保搜索结果可见
        self.year_filter.setCurrentIndex(0)  # 所有年份
        self.month_filter.setCurrentIndex(0)  # 所有月份
        self.status_filter.setCurrentIndex(0)  # 全部状态
        if hasattr(self, 'debtors_toggle'):
            self.debtors_toggle.setChecked(False)  # 取消"只看欠款"
            
        self.search_input.setText(query)
        # 触发搜索
        self._apply_filters()

    def _init_ui(self):
        """初始化财务管理界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 顶部操作区域 (卡片样式)
        top_frame = QFrame()
        top_frame.setProperty("class", "card")
        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(10)
        
        # 第一行：搜索框
        row1_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索财务记录...')
        self.search_input.textChanged.connect(self._apply_filters)
        row1_layout.addWidget(self.search_input)
        top_layout.addLayout(row1_layout)
        
        # 第二行：筛选和操作按钮
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(15)
        
        # 年份筛选控件
        self.year_filter = QComboBox()
        self.year_filter.addItem('所有年份')
        self._load_year_filter()
        self.year_filter.currentIndexChanged.connect(self._update_month_filter)
        self.year_filter.currentIndexChanged.connect(self._apply_filters)
        row2_layout.addWidget(QLabel('选择年份:'))
        row2_layout.addWidget(self.year_filter)
        
        # 月份筛选控件
        self.month_filter = QComboBox()
        self.month_filter.addItem('所有月份')
        self.month_filter.setEnabled(False)
        self.month_filter.currentIndexChanged.connect(self._apply_filters)
        row2_layout.addWidget(QLabel('选择月份:'))
        row2_layout.addWidget(self.month_filter)
        
        # 收款状态筛选
        self.status_filter = QComboBox()
        self.status_filter.addItems(['全部', '待收款', '已逾期', '已结清'])
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        row2_layout.addWidget(QLabel('收款状态:'))
        row2_layout.addWidget(self.status_filter)

        # 排序下拉框
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            '默认排序 (日期)',
            '日期 (新→旧)',
            '日期 (旧→新)',
            '金额 (高→低)',
            '金额 (低→高)'
        ])
        # 设置下拉列表的最小宽度，使其比点击框更宽以显示完整内容
        self.sort_combo.view().setMinimumWidth(150)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        row2_layout.addWidget(QLabel('排序:'))
        row2_layout.addWidget(self.sort_combo)
        
        # 只看欠款
        self.debtors_toggle = QPushButton('只看欠款')
        self.debtors_toggle.setCheckable(True)
        self.debtors_toggle.toggled.connect(self._apply_filters)
        row2_layout.addWidget(self.debtors_toggle)
        
        row2_layout.addStretch() # 中间弹簧
        
        add_btn = QPushButton('新增记录')
        add_btn.setProperty("class", "success")
        add_btn.clicked.connect(lambda: self._show_add_dialog())
        row2_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton('刷新')
        refresh_btn.setProperty("class", "primary")
        refresh_btn.clicked.connect(self._load_finance)
        row2_layout.addWidget(refresh_btn)
        
        stats_btn = QPushButton('查看统计')
        stats_btn.setProperty("class", "warning")
        stats_btn.clicked.connect(self._show_stats)
        row2_layout.addWidget(stats_btn)
        
        # 添加导入导出按钮
        import_btn = QPushButton('导入')
        import_btn.setProperty("class", "info")
        import_btn.clicked.connect(self._import_finance)
        row2_layout.addWidget(import_btn)
        
        export_btn = QPushButton('导出')
        export_btn.setProperty("class", "info")
        export_btn.clicked.connect(self._export_finance)
        row2_layout.addWidget(export_btn)
        
        top_layout.addLayout(row2_layout)
        main_layout.addWidget(top_frame)
        
        # 财务列表区域 (卡片样式)
        list_frame = QFrame()
        list_frame.setProperty("class", "card")
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(12, 12, 12, 12)
        
        control_layout = QHBoxLayout()
        select_all_btn = QPushButton('全选')
        select_all_btn.clicked.connect(self._select_all_rows)
        invert_btn = QPushButton('反选')
        invert_btn.clicked.connect(self._invert_selection)
        clear_btn = QPushButton('取消选择')
        clear_btn.clicked.connect(self._clear_selection)
        delete_selected_btn = QPushButton('删除选中')
        delete_selected_btn.setProperty("class", "danger")
        delete_selected_btn.clicked.connect(self._delete_selected_finance)
        control_layout.addWidget(select_all_btn)
        control_layout.addWidget(invert_btn)
        control_layout.addWidget(clear_btn)
        control_layout.addWidget(delete_selected_btn)
        list_layout.addLayout(control_layout)
        
        # 使用 QListWidget 替换 QTableWidget
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.NoFrame)
        self.list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_widget.setSpacing(12)
        # self.list_widget.setContentsMargins(6, 0, 6, 0)
        # 启用图标模式以支持自动排列（网格布局）
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        # 设置网格大小，确保比卡片稍大，防止重叠且左右留出一致边距
        self.list_widget.setGridSize(QSize(372, 266))
        self.list_widget.setStyleSheet("QListWidget { background: transparent; }")
        
        list_layout.addWidget(self.list_widget)
        
        # Pagination Controls
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(self._prev_page)
        self.prev_btn.setEnabled(False)
        pagination_layout.addWidget(self.prev_btn)
        
        self.page_label = QLabel("第 1 / 1 页")
        self.page_label.setStyleSheet("color: #606266; margin: 0 10px;")
        pagination_layout.addWidget(self.page_label)
        
        self.next_btn = QPushButton("下一页")
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.clicked.connect(self._next_page)
        self.next_btn.setEnabled(False)
        pagination_layout.addWidget(self.next_btn)
        
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

        pagination_layout.addSpacing(5)
        pagination_layout.addWidget(jump_container)
        pagination_layout.addStretch()
        list_layout.addLayout(pagination_layout)
        
        main_layout.addWidget(list_frame)
        
        stats_frame = QFrame()
        stats_frame.setProperty("class", "card")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(10, 8, 10, 8)
        stats_layout.addWidget(QLabel('总利润:'))
        self.stats_profit_label = QLabel('¥0.00')
        self.stats_profit_label.setStyleSheet('font-weight: bold;')
        stats_layout.addWidget(self.stats_profit_label)
        stats_layout.addStretch()
        stats_layout.addWidget(QLabel('当前待收总额:'))
        self.stats_pending_label = QLabel('¥0.00')
        self.stats_pending_label.setStyleSheet('font-weight: bold; color: #e6a23c;')
        stats_layout.addWidget(self.stats_pending_label)
        main_layout.addWidget(stats_frame)
        
        self.setLayout(main_layout)
        
    def _fetch_data_worker(self, search_text, year_filter, month_filter, status_filter, only_debtors, sort_option, limit, offset):
        """Background worker to fetch data and count"""
        conn = self.db_manager.create_new_connection()
        try:
            cursor = conn.cursor()
            
            where_clauses = ["is_deleted = 0"]
            params = []
            
            # Search
            if search_text:
                where_clauses.append("(company_name LIKE ? OR CAST(amount AS TEXT) LIKE ? OR due_date LIKE ? OR notes LIKE ?)")
                p = f"%{search_text}%"
                params.extend([p, p, p, p])
            
            # Year/Month
            if year_filter != '所有年份':
                where_clauses.append("strftime('%Y', due_date) = ?")
                params.append(year_filter)
                if month_filter != '所有月份':
                    where_clauses.append("strftime('%m', due_date) = ?")
                    params.append(month_filter)
            
            # Status & Debtors
            today = datetime.now().strftime('%Y-%m-%d')
            
            if status_filter == '待收款':
                where_clauses.append("pending_amount > 0 AND (pending_date IS NULL OR pending_date = '' OR pending_date >= ?)")
                params.append(today)
            elif status_filter == '已逾期':
                where_clauses.append("pending_amount > 0 AND pending_date < ? AND pending_date != ''")
                params.append(today)
            elif status_filter == '已结清':
                where_clauses.append("pending_amount <= 0")
            
            if only_debtors:
                where_clauses.append("pending_amount > 0")
                
            where_sql = " AND ".join(where_clauses)
            
            # Count
            count_sql = f"SELECT COUNT(*) FROM finance WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # Stats (Total Profit & Pending for current filter)
            stats_sql = f"""
                SELECT SUM(profit), SUM(pending_amount)
                FROM finance
                WHERE {where_sql}
            """
            cursor.execute(stats_sql, params)
            stats_row = cursor.fetchone()
            total_profit = stats_row[0] or 0.0
            total_pending = stats_row[1] or 0.0
            
            # Determine Order
            order_by = "due_date DESC"
            if sort_option == '日期 (新→旧)':
                order_by = "due_date DESC"
            elif sort_option == '日期 (旧→新)':
                order_by = "due_date ASC"
            elif sort_option == '金额 (高→低)':
                order_by = "amount DESC"
            elif sort_option == '金额 (低→高)':
                order_by = "amount ASC"

            # Data
            sql = f"""
                SELECT id, company_name, amount, 
                       cost, profit, due_date, notes,
                       pending_amount, pending_date,
                       payment_method, contract_status,
                       project_status, invoice_status
                FROM finance
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            cursor.execute(sql, params + [limit, offset])
            rows = cursor.fetchall()
            
            return rows, total, total_profit, total_pending
            
        finally:
            conn.close()

    def _load_finance(self):
        """Async load finance data"""
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.list_widget.clear()
        self._cards = []
        
        # Get filter params
        search_text = self.search_input.text().strip()
        year_filter = self.year_filter.currentText()
        month_filter = self.month_filter.currentText()
        status_filter = self.status_filter.currentText()
        sort_option = self.sort_combo.currentText()
        only_debtors = self.debtors_toggle.isChecked()
        
        offset = (self.page - 1) * self.page_size
        
        worker = Worker(self._fetch_data_worker, search_text, year_filter, month_filter, status_filter, only_debtors, sort_option, self.page_size, offset)
        worker.signals.result.connect(self._on_load_success)
        worker.signals.error.connect(self._on_load_error)
        self.threadpool.start(worker)

    def _on_sort_changed(self):
        self.page = 1
        self._load_finance()

    def _jump_to_page(self):
        text = self.jump_input.text().strip()
        if not text:
            return
        try:
            page = int(text)
            if 1 <= page <= self.total_pages:
                self.page = page
                self._load_finance()
                self.jump_input.clear()
            else:
                QMessageBox.warning(self, "提示", f"请输入 1 到 {self.total_pages} 之间的页码")
                self.jump_input.selectAll()
                self.jump_input.setFocus()
        except ValueError:
            pass

    def _on_load_success(self, result):
        rows, total, total_profit, total_pending = result
        self.total_count = total
        self.total_pages = (self.total_count + self.page_size - 1) // self.page_size
        if self.total_pages == 0: self.total_pages = 1
        
        self.list_widget.clear()
        self._cards = []
        
        for finance in rows:
            # 解包所有字段
            if len(finance) >= 13:
                fin_id, company_name, amount, cost, profit, due_date, notes, pending_amount, pending_date, payment_method, contract_status, project_status, invoice_status = finance
            else:
                # 兼容旧结构
                fin_id, company_name, amount, cost, profit, due_date, notes, pending_amount, pending_date = finance[:9]
                payment_method = contract_status = project_status = invoice_status = None
            
            data = {
                'id': fin_id,
                'company_name': company_name,
                'amount': amount,
                'cost': cost,
                'profit': profit,
                'due_date': due_date,
                'notes': notes,
                'pending_amount': pending_amount or 0.0,
                'pending_date': pending_date or '',
                'payment_method': payment_method or '',
                'contract_status': contract_status or '',
                'project_status': project_status or '',
                'invoice_status': invoice_status or ''
            }
            
            # 创建卡片
            card = FinanceCardWidget(data)
            card.set_callback('edit', lambda d=data: self._edit_finance(d))
            card.set_callback('delete', lambda d=data: self._delete_finance(d))
            self._cards.append(card)
            
            # 添加到列表
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(360, 250)) 
            self.list_widget.setItemWidget(item, card)
            
        # Update UI
        self.page_label.setText(f"第 {self.page} / {self.total_pages} 页")
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < self.total_pages)
        
        # Update stats
        self.stats_profit_label.setText(f'¥{total_profit:.2f}')
        self.stats_pending_label.setText(f'¥{total_pending:.2f}')

        # 处理待处理的选中请求
        if self.pending_select_query:
            query = self.pending_select_query
            self.pending_select_query = None
            
            # 尝试查找匹配项
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                card = self.list_widget.itemWidget(item)
                if card:
                    data = card.data
                    if query in data.get('company_name', ''):
                        item.setSelected(True)
                        self.list_widget.setCurrentItem(item)
                        self.list_widget.scrollToItem(item)
                        # 触发选中视觉效果(如果需要)
                        if hasattr(card, 'set_checked'):
                            card.set_checked(True)
                        break

    def _on_load_error(self, error):
        logger.error(f"Error loading finance data: {error}")
        self.list_widget.clear()
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        QMessageBox.warning(self, "错误", "加载数据失败，请重试")

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_finance()
            
    def _next_page(self):
        if self.page < self.total_pages:
            self.page += 1
            self._load_finance()

    def _apply_filters(self):
        # Reset to page 1 and reload
        self.page = 1
        self._load_finance()
            
    def _load_year_filter(self):
        """加载可选年份"""
        with self.db_manager.conn:
            cursor = self.db_manager.conn.cursor()
            cursor.execute('SELECT DISTINCT strftime("%Y", due_date) FROM finance ORDER BY due_date DESC')
            years = cursor.fetchall()
            
            for year in years:
                self.year_filter.addItem(year[0])
                
    def _update_month_filter(self):
        """根据选中的年份动态加载月份"""
        selected_year = self.year_filter.currentText()
        self.month_filter.clear()
        self.month_filter.addItem('所有月份')
        
        if selected_year == '所有年份':
            self.month_filter.setEnabled(False)
            return
            
        self.month_filter.setEnabled(True)
        with self.db_manager.conn:
            cursor = self.db_manager.conn.cursor()
            cursor.execute('SELECT DISTINCT strftime("%m", due_date) FROM finance WHERE strftime("%Y", due_date) = ? ORDER BY due_date', (selected_year,))
            months = cursor.fetchall()
            
            for month in months:
                self.month_filter.addItem(month[0])
        self._apply_filters()
                
    def _update_stats(self):
        total_profit = 0.0
        total_pending = 0.0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.isHidden():
                continue
            card = self.list_widget.itemWidget(item)
            data = card.data
            total_profit += float(data.get('profit', 0) or 0)
            total_pending += float(data.get('pending_amount', 0) or 0)
        self.stats_profit_label.setText(f'¥{total_profit:.2f}')
        self.stats_pending_label.setText(f'¥{total_pending:.2f}')
            
    # 已移除客户筛选功能
            
    def _show_add_dialog(self, finance_data=None):
        """显示添加/编辑财务记录对话框"""
        dialog = FinanceEditDialog(self.db_manager, finance_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_finance()
            
    def _edit_finance(self, data):
        """编辑财务信息"""
        try:
            self._show_add_dialog(data)
        except Exception as e:
            QMessageBox.warning(self, '错误', f'编辑失败: {str(e)}')

        
    def _delete_finance(self, data):
        """删除财务记录"""
        try:
            company_name = data.get('company_name', '')
            fin_id = data.get('id', 0)
            
            reply = QMessageBox.question(
                self, 
                '确认删除', 
                f'确定要删除 "{company_name}" 的财务记录吗?', 
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                with self.db_manager.conn:
                    cursor = self.db_manager.conn.cursor()
                    from datetime import datetime
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute('UPDATE finance SET is_deleted = 1, deleted_at = ? WHERE id = ?', (now, fin_id))
                    
                self._load_finance()
        except Exception as e:
            QMessageBox.warning(self, '错误', f'删除失败: {str(e)}')
            
    def _show_stats(self):
        """显示财务统计图表"""
        # 直接显示统计窗口，无需预先筛选
        stats_window = FinanceStatsWindow(self.db_manager, self)
        stats_window.exec_()

        
    def _get_monthly_stats(self, filters=None):
        """获取月度财务统计数据"""
        monthly_stats = {}
        filters = filters or {}
        
        with self.db_manager.conn:
            cursor = self.db_manager.conn.cursor()
            
            query = '''
                SELECT strftime('%Y-%m', due_date) as month,
                       SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
                       SUM(CASE WHEN cost > 0 THEN cost ELSE 0 END) as expense,
                       SUM(profit) as profit
                FROM finance
                WHERE is_deleted = 0
            '''
            params = []
            
            if 'company' in filters:
                query += " AND company_name LIKE ?"
                params.append(f"%{filters['company']}%")
                
            if 'start_date' in filters:
                query += " AND due_date >= ?"
                params.append(filters['start_date'])
                
            if 'end_date' in filters:
                query += " AND due_date <= ?"
                params.append(filters['end_date'])
                
            query += '''
                GROUP BY month
                ORDER BY month
            '''
            
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                month, income, expense, profit = row
                monthly_stats[month] = {
                    'income': income or 0,
                    'expense': expense or 0,
                    'profit': profit or 0
                }
                
        return monthly_stats
        
    def _export_finance(self):
        """导出财务数据为Excel格式"""
        # 1. 弹出筛选对话框
        dialog = FinanceFilterDialog(
            self.db_manager, 
            self, 
            title='导出选项', 
            confirm_text='导出',
            hint_text='提示: 项目名称留空且不勾选日期筛选，将导出所有数据'
        )
        if dialog.exec_() != QDialog.Accepted:
            return
            
        filters = dialog.get_filters()
        
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        
        # 生成默认文件名
        filename_parts = ['财务数据']
        if 'company' in filters:
            filename_parts.append(filters['company'])
        if 'start_date' in filters:
            filename_parts.append(f"{filters['start_date']}至{filters['end_date']}")
        else:
            filename_parts.append(datetime.now().strftime("%Y%m%d"))
            
        default_filename = f"{'_'.join(filename_parts)}.xlsx"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            '导出财务数据',
            default_filename,
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
                
                # 构建查询语句
                query = '''
                    SELECT 
                        company_name, amount, cost, 
                        profit, due_date, notes,
                        pending_amount, pending_date
                    FROM finance
                    WHERE is_deleted = 0
                '''
                params = []
                
                # 应用筛选条件
                if 'company' in filters:
                    query += " AND company_name LIKE ?"
                    params.append(f"%{filters['company']}%")
                    
                if 'start_date' in filters:
                    query += " AND due_date >= ?"
                    params.append(filters['start_date'])
                    
                if 'end_date' in filters:
                    query += " AND due_date <= ?"
                    params.append(filters['end_date'])
                    
                query += " ORDER BY due_date DESC"
                
                # 检查数据量
                count_query = f"SELECT COUNT(*) FROM ({query})"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    QMessageBox.warning(self, '警告', '没有符合筛选条件的数据可导出')
                    return
                    
                # 执行查询
                logger.info(f"Exporting finance data with filters: {filters}")
                cursor.execute(query, params)
                
                rows = cursor.fetchall()
                logger.info(f"Found {len(rows)} records")
                
                # 定义表头和数据库字段映射
                columns = ['company_name', 'amount', 'cost', 'profit', 'due_date', 'notes', 'pending_amount', 'pending_date']
                headers = ['项目名称', '金额', '成本', '利润', '项目日期', '备注', '待收金额', '待收日期']
                data = []
                
                # 严格验证和转换每条记录
                for i, row in enumerate(rows, 1):
                    try:
                        # 验证字段数量
                        if len(row) != len(columns):
                            raise ValueError(f"记录字段数不匹配，预期{len(columns)}，实际{len(row)}")
                            
                        # 创建数据字典，确保键与表头对应
                        row_dict = {
                            'company_name': str(row[0]) if row[0] is not None else '',
                            'amount': float(row[1]) if row[1] is not None else 0.0,
                            'cost': float(row[2]) if row[2] is not None else 0.0,
                            'profit': float(row[3]) if row[3] is not None else 0.0,
                            'due_date': str(row[4]) if row[4] is not None else '',
                            'notes': str(row[5]) if row[5] is not None else '',
                            'pending_amount': float(row[6]) if row[6] is not None else 0.0,
                            'pending_date': str(row[7]) if row[7] is not None else ''
                        }
                        
                        # 转换为导出所需的格式
                        export_row = {
                            headers[0]: row_dict['company_name'],
                            headers[1]: str(row_dict['amount']),
                            headers[2]: str(row_dict['cost']),
                            headers[3]: str(row_dict['profit']),
                            headers[4]: row_dict['due_date'],
                            headers[5]: row_dict['notes'],
                            headers[6]: str(row_dict['pending_amount']),
                            headers[7]: row_dict['pending_date']
                        }
                        
                        data.append(export_row)
                        
                    except Exception as e:
                        logger.error(f"\n!!! Error converting record {i}: {str(e)}")
                        raise ValueError(f"数据处理失败: {str(e)}")
                
                # 使用BaseImporterExporter导出
                from core.import_export import BaseImporterExporter, ImportExportError
                exporter = BaseImporterExporter()
                if not hasattr(exporter, 'export_to_excel'):
                    raise Exception("BaseImporterExporter缺少export_to_excel方法")
                    
                exporter.export_to_excel(
                    data=data,
                    file_path=file_path,
                    sheet_name='财务数据',
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
                    f'财务数据已成功导出到:\n{file_path}\n'
                    f'共导出 {len(data)} 条记录\n'
                    f'文件大小: {file_size/1024:.1f}KB'
                )
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Export error details:\n{error_details}")
            
            QMessageBox.critical(
                self, 
                '导出失败', 
                f'导出过程中发生错误:\n{str(e)}\n'
                '详细错误已记录到控制台'
            )
            
    def _import_finance(self):
        """从Excel文件导入财务数据"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from core.import_export import BaseImporterExporter
        from datetime import datetime
        from core.import_export import ImportExportError
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择财务数据文件',
            '',
            'Excel文件 (*.xlsx)'
        )
        
        if not file_path:
            return
            
        try:
            # 初始化导入器
            importer = BaseImporterExporter()
            importer._required_columns = ['项目名称', '金额']
            importer._column_mapping = {
                '项目名称': 'company_name',
                '金额': 'amount',
                '成本': 'cost',
                '项目日期': 'due_date',
                '备注': 'notes',
                '待收金额': 'pending_amount',
                '待收日期': 'pending_date'
            }
            
            # 获取现有数据用于去重
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.execute('SELECT company_name, due_date FROM finance')
                existing_finance = [{'company_name': row[0], 'due_date': row[1]} 
                                  for row in cursor.fetchall()]
                importer.cache_existing_data(
                    existing_finance,
                    key_columns=['company_name', 'due_date']
                )
            
            # 从Excel导入数据
            imported_data = importer.import_from_excel(
                file_path=file_path,
                sheet_name='财务数据',
                key_columns=['company_name', 'due_date'],
                skip_duplicates=True
            )
            
            if not imported_data:
                QMessageBox.information(self, '导入完成', '没有可导入的数据')
                return
                
            # 准备导入数据
            records_to_insert = []
            for row in imported_data:
                # 计算利润
                amount = float(row.get('amount', 0))
                cost = float(row.get('cost', 0))
                profit = amount - cost
                
                records_to_insert.append((
                    row.get('company_name', ''),
                    amount,
                    cost,
                    profit,
                    row.get('due_date', ''),
                    row.get('notes', ''),
                    float(row.get('pending_amount', 0)),
                    row.get('pending_date', '')
                ))
            
            # 执行批量导入
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                cursor.executemany('''
                    INSERT OR IGNORE INTO finance (
                        company_name, amount, cost, profit, 
                        due_date, notes, pending_amount, pending_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', records_to_insert)
                
                inserted_count = cursor.rowcount
                total_count = len(imported_data)
                skipped_count = total_count - inserted_count
                
            # 刷新界面和数据
            self._load_finance()
            
            # 显示导入结果
            QMessageBox.information(
                self,
                '导入完成',
                f'成功导入 {inserted_count} 条财务记录\n'
                f'跳过 {skipped_count} 条重复记录\n'
                f'共处理 {total_count} 条记录'
            )
            
        except ImportExportError as e:
            QMessageBox.critical(self, '导入错误', str(e))
        except Exception as e:
            QMessageBox.critical(
                self,
                '导入失败',
                f'导入过程中发生错误:\n{str(e)}\n'
                '请检查文件格式是否正确'
            )
    
    def _select_all_rows(self):
        for card in getattr(self, '_cards', []):
            card.set_checked(True)
    
    def _invert_selection(self):
        for card in getattr(self, '_cards', []):
            card.set_checked(not card.is_checked())
    
    def _clear_selection(self):
        for card in getattr(self, '_cards', []):
            card.set_checked(False)
    
    def _delete_selected_finance(self):
        ids = [card.data.get('id') for card in getattr(self, '_cards', []) if card.is_checked()]
        if not ids:
            return
        reply = QMessageBox.question(
            self, 
            '确认删除', 
            f'确定要删除选中的 {len(ids)} 条记录吗?', 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            with self.db_manager.conn:
                cursor = self.db_manager.conn.cursor()
                # 使用 executemany 进行批量删除
                from datetime import datetime
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.executemany('UPDATE finance SET is_deleted = 1, deleted_at = ? WHERE id = ?', [(now, i) for i in ids])
                
            self._load_finance()

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = FinanceWindow(None)
    window.show()
    sys.exit(app.exec_())
