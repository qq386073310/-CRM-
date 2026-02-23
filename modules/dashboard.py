from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QMessageBox, QPushButton, 
                             QCheckBox, QTextEdit, QFrame, QInputDialog, 
                             QDateEdit, QSizePolicy, QScrollArea,
                             QSpinBox, QListWidget, QListWidgetItem, QMenu, QTabWidget)
from PyQt5.QtChart import (QChart, QChartView, QLineSeries, QSplineSeries,
                          QValueAxis, QBarCategoryAxis, QPieSeries, QPieSlice)
from PyQt5.QtCore import Qt, QDate, QSettings, QMargins, QSize
from PyQt5.QtGui import QPainter, QColor, QFont
from core.logger import logger

class DashboardWindow(QWidget):
    def __init__(self, main_window=None):
        """初始化仪表板窗口"""
        super().__init__()
        
        # 保存主窗口引用
        self.main_window = main_window
        if main_window:
            self.db_manager = main_window.app.db_manager
            
        # 初始化设置
        self.settings = QSettings("CustomerManagement", "Dashboard")
        
        # 主布局
        self.dashboard_layout = QVBoxLayout()
        self.dashboard_layout.setContentsMargins(10, 10, 10, 10)
        self.dashboard_layout.setSpacing(10)
        self.setLayout(self.dashboard_layout)
        
        # 1. 顶部卡片区域
        self._create_card_area()
        
        # 2. 中间图表区域
        self._create_chart_area()
        
        # 3. 底部功能区域
        self._create_function_area()
        
        # 初始化数据
        self.update_data()

    def _update_day_combo(self, year_combo, month_combo, day_combo):
        """更新日下拉框的选项"""
        current_day = day_combo.currentText()
        year = int(year_combo.currentText())
        month = int(month_combo.currentText())
        days_in_month = QDate(year, month, 1).daysInMonth()
        
        day_combo.clear()
        day_combo.addItems([f"{day:02d}" for day in range(1, days_in_month + 1)])
        
        if current_day:
            day_combo.setCurrentText(current_day)
            
    def _set_this_month(self):
        """设置为本月"""
        today = QDate.currentDate()
        self.start_year_combo.setCurrentText(str(today.year()))
        self.start_month_combo.setCurrentText(f"{today.month():02d}")
        self.start_day_combo.setCurrentText("01")
        
        self.end_year_combo.setCurrentText(str(today.year()))
        self.end_month_combo.setCurrentText(f"{today.month():02d}")
        self.end_day_combo.setCurrentText(f"{today.day():02d}")
        
        self.update_data()

    def _set_all_time(self):
        """设置为全部时间"""
        today = QDate.currentDate()
        # 设置为最早年份
        if self.start_year_combo.count() > 0:
            self.start_year_combo.setCurrentIndex(0)
            self.start_month_combo.setCurrentText("01")
            self.start_day_combo.setCurrentText("01")
        
        self.end_year_combo.setCurrentText(str(today.year()))
        self.end_month_combo.setCurrentText(f"{today.month():02d}")
        self.end_day_combo.setCurrentText(f"{today.day():02d}")
        
        self.update_data()
        
    def _create_card_area(self):
        """创建顶部卡片区域"""
        # 日期选择区域
        date_frame = QFrame()
        date_frame.setObjectName("date_filter_panel")
        date_frame.setProperty("class", "card")
        date_layout = QHBoxLayout(date_frame)
        date_layout.setContentsMargins(15, 10, 15, 10)
        date_layout.setSpacing(10)
        
        # 开始日期选择（年、月、日）
        date_layout.addWidget(QLabel("开始日期:"))
        
        # 年下拉框
        self.start_year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        self.start_year_combo.addItems([str(year) for year in range(current_year - 10, current_year + 1)])
        self.start_year_combo.setCurrentText(str(current_year))
        date_layout.addWidget(self.start_year_combo)
        
        # 月下拉框
        self.start_month_combo = QComboBox()
        self.start_month_combo.addItems([f"{month:02d}" for month in range(1, 13)])
        self.start_month_combo.setCurrentText(f"{QDate.currentDate().month():02d}")
        date_layout.addWidget(self.start_month_combo)
        
        # 日下拉框
        self.start_day_combo = QComboBox()
        self._update_day_combo(self.start_year_combo, self.start_month_combo, self.start_day_combo)
        date_layout.addWidget(self.start_day_combo)
        
        # 绑定事件
        self.start_year_combo.currentTextChanged.connect(
            lambda: self._update_day_combo(self.start_year_combo, self.start_month_combo, self.start_day_combo)
        )
        self.start_month_combo.currentTextChanged.connect(
            lambda: self._update_day_combo(self.start_year_combo, self.start_month_combo, self.start_day_combo)
        )
        
        date_layout.addWidget(QLabel("至"))
        
        # 结束日期选择（年、月、日）
        date_layout.addWidget(QLabel("结束日期:"))
        
        # 年下拉框
        self.end_year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        self.end_year_combo.addItems([str(year) for year in range(current_year - 10, current_year + 1)])
        self.end_year_combo.setCurrentText(str(current_year))
        date_layout.addWidget(self.end_year_combo)
        
        # 月下拉框
        self.end_month_combo = QComboBox()
        self.end_month_combo.addItems([f"{month:02d}" for month in range(1, 13)])
        self.end_month_combo.setCurrentText(f"{QDate.currentDate().month():02d}")
        date_layout.addWidget(self.end_month_combo)
        
        # 日下拉框
        self.end_day_combo = QComboBox()
        self._update_day_combo(self.end_year_combo, self.end_month_combo, self.end_day_combo)
        # 默认选中今天
        self.end_day_combo.setCurrentText(f"{QDate.currentDate().day():02d}")
        date_layout.addWidget(self.end_day_combo)
        
        # 绑定事件
        self.end_year_combo.currentTextChanged.connect(
            lambda: self._update_day_combo(self.end_year_combo, self.end_month_combo, self.end_day_combo)
        )
        self.end_month_combo.currentTextChanged.connect(
            lambda: self._update_day_combo(self.end_year_combo, self.end_month_combo, self.end_day_combo)
        )
        
        # 快速筛选按钮
        self.btn_this_month = QPushButton("本月")
        self.btn_this_month.setCursor(Qt.PointingHandCursor)
        self.btn_this_month.clicked.connect(self._set_this_month)
        date_layout.addWidget(self.btn_this_month)

        self.btn_all_time = QPushButton("全部")
        self.btn_all_time.setCursor(Qt.PointingHandCursor)
        self.btn_all_time.clicked.connect(self._set_all_time)
        date_layout.addWidget(self.btn_all_time)
        
        date_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setProperty("class", "primary")
        self.refresh_btn.clicked.connect(self.update_data)
        date_layout.addWidget(self.refresh_btn)
        
        self.dashboard_layout.addWidget(date_frame)
        
        # 卡片布局
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)
        
        # 创建4个卡片
        self.total_customers_card = self._create_card("总客户数", "0", "#409eff")
        self.total_transactions_card = self._create_card("总交易量", "0", "#67c23a")
        self.monthly_income_card = self._create_card("本月收入", "¥0", "#e6a23c")
        self.monthly_profit_card = self._create_card("本月利润", "¥0", "#f56c6c")
        
        # 添加卡片到布局
        cards_layout.addWidget(self.total_customers_card)
        cards_layout.addWidget(self.total_transactions_card)
        cards_layout.addWidget(self.monthly_income_card)
        cards_layout.addWidget(self.monthly_profit_card)
        
        self.dashboard_layout.addLayout(cards_layout)

    def _create_card(self, title, value, color_code):
        """创建单个卡片"""
        card = QFrame()
        card.setProperty("class", "card")
        # 只需要设置左边框颜色，其他样式由class="card"控制
        card.setStyleSheet(f"""
            QFrame[class="card"] {{
                border-left: 5px solid {color_code};
            }}
            QFrame[class="card"]:hover {{
                border: 1px solid {color_code};
                border-left: 5px solid {color_code};
            }}
        """)
        
        layout = QVBoxLayout(card)
        # 减小内边距，使卡片高度变低
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setProperty("class", "card-title")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setProperty("class", "card-value")
        layout.addWidget(value_label)
        
        return card

    def _create_chart_area(self):
        """创建中间图表区域"""
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(20)
        
        # --- 左侧：图表 ---
        chart_frame = QFrame()
        chart_frame.setProperty("class", "card")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(10, 10, 10, 10) # 减少边距以适应Tab
        
        # 使用 TabWidget 切换图表
        self.chart_tabs = QTabWidget()
        
        # 1. 月度收支趋势 Tab
        self.trends_tab = QWidget()
        trends_layout = QVBoxLayout(self.trends_tab)
        
        # 趋势图标题栏
        header_layout = QHBoxLayout()
        # 年份选择
        self.year_combo = QComboBox()
        current_year = QDate.currentDate().year()
        self.year_combo.addItems([str(year) for year in range(current_year - 5, current_year + 1)])
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.update_chart)
        
        header_layout.addStretch()
        header_layout.addWidget(QLabel("年份:"))
        header_layout.addWidget(self.year_combo)
        trends_layout.addLayout(header_layout)
        
        # 创建趋势图表
        self.monthly_chart = QChart()
        # 主题设置将在 update_chart 中处理
        self.monthly_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.monthly_chart.setMargins(QMargins(45, 10, 20, 10))
        
        chart_view = QChartView(self.monthly_chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        trends_layout.addWidget(chart_view)
        
        self.chart_tabs.addTab(self.trends_tab, "月度收支趋势")
        
        # 2. 业务类型分布 Tab
        self.distribution_tab = QWidget()
        dist_layout = QVBoxLayout(self.distribution_tab)
        
        # 创建饼图
        self.pie_chart = QChart()
        self.pie_chart.setAnimationOptions(QChart.SeriesAnimations)
        self.pie_chart.legend().setAlignment(Qt.AlignRight)
        
        pie_view = QChartView(self.pie_chart)
        pie_view.setRenderHint(QPainter.Antialiasing)
        dist_layout.addWidget(pie_view)
        
        self.chart_tabs.addTab(self.distribution_tab, "业务类型分布")
        
        chart_layout.addWidget(self.chart_tabs)
        
        middle_layout.addWidget(chart_frame, 2) # 比例 2 (图表占 2/3)
        
        # --- 右侧：容器 ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(20)
        
        reminder_frame = QFrame()
        reminder_frame.setProperty("class", "card")
        reminder_layout = QVBoxLayout(reminder_frame)
        
        # 标题栏
        reminder_header = QHBoxLayout()
        reminder_title = QLabel("到期提醒")
        reminder_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        reminder_header.addWidget(reminder_title)
        
        reminder_header.addStretch()
        
        # 设置天数
        self.reminder_days = QSpinBox()
        self.reminder_days.setRange(1, 365)
        self.reminder_days.setValue(int(self.settings.value("reminder_days", 30)))
        self.reminder_days.setToolTip("提前提醒天数")
        self.reminder_days.valueChanged.connect(self._save_reminder_settings)
        self.reminder_days.valueChanged.connect(self._load_reminders)
        reminder_header.addWidget(QLabel("天数:"))
        reminder_header.addWidget(self.reminder_days)
        
        reminder_layout.addLayout(reminder_header)
        
        # 提醒列表区域 (使用 ScrollArea + VBoxLayout 替代 QListWidget 以获得更好的控制权)
        self.reminder_scroll = QScrollArea()
        self.reminder_scroll.setWidgetResizable(True)
        self.reminder_scroll.setFrameShape(QFrame.NoFrame)
        self.reminder_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.reminder_container = QWidget()
        self.reminder_layout = QVBoxLayout(self.reminder_container)
        self.reminder_layout.setContentsMargins(0, 0, 0, 0)
        self.reminder_layout.setSpacing(0) # 紧凑布局
        
        self.reminder_scroll.setWidget(self.reminder_container)
        
        # 设置透明背景，适配深色模式
        self.reminder_scroll.setStyleSheet("background: transparent;")
        self.reminder_container.setStyleSheet("background: transparent;")
        
        reminder_layout.addWidget(self.reminder_scroll)
        
        # 提示标签
        tip_label = QLabel("右键点击条目可忽略提醒")
        tip_label.setStyleSheet("color: #909399; font-size: 12px;")
        tip_label.setAlignment(Qt.AlignCenter)
        reminder_layout.addWidget(tip_label)
        
        right_layout.addWidget(reminder_frame)
        
        receivable_frame = QFrame()
        receivable_frame.setProperty("class", "card")
        receivable_frame.setMinimumHeight(150)
        receivable_layout = QVBoxLayout(receivable_frame)
        
        receivable_header = QHBoxLayout()
        receivable_title = QLabel("近期应收账款")
        receivable_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        receivable_header.addWidget(receivable_title)
        receivable_header.addStretch()
        receivable_layout.addLayout(receivable_header)
        
        self.receivable_scroll = QScrollArea()
        self.receivable_scroll.setWidgetResizable(True)
        self.receivable_scroll.setFrameShape(QFrame.NoFrame)
        self.receivable_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.receivable_container = QWidget()
        self.receivable_items_layout = QVBoxLayout(self.receivable_container)
        self.receivable_items_layout.setContentsMargins(0, 0, 0, 0)
        self.receivable_items_layout.setSpacing(0)
        
        self.receivable_scroll.setWidget(self.receivable_container)
        self.receivable_scroll.setStyleSheet("background: transparent;")
        self.receivable_container.setStyleSheet("background: transparent;")
        
        receivable_layout.addWidget(self.receivable_scroll)
        
        right_layout.addWidget(receivable_frame)
        
        middle_layout.addWidget(right_panel, 1)
        
        self.dashboard_layout.addLayout(middle_layout, 1) # 给予拉伸因子，让图表区域占据主要垂直空间

    def _create_function_area(self):
        """创建底部功能区域 (待办事项 + 便签)"""
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        # 1. 待办事项
        todo_frame = QFrame()
        todo_frame.setProperty("class", "card")
        todo_layout = QVBoxLayout(todo_frame)
        
        # 标题栏
        todo_header = QHBoxLayout()
        todo_title = QLabel("待办事项")
        todo_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        todo_header.addWidget(todo_title)
        todo_header.addStretch()
        
        add_todo_btn = QPushButton("+")
        add_todo_btn.setFixedSize(24, 24)
        add_todo_btn.setProperty("class", "success small-btn")
        add_todo_btn.clicked.connect(self._add_todo_item)
        todo_header.addWidget(add_todo_btn)
        
        self.delete_todo_btn = QPushButton("-")
        self.delete_todo_btn.setFixedSize(24, 24)
        self.delete_todo_btn.setProperty("class", "danger small-btn")
        self.delete_todo_btn.clicked.connect(self._delete_selected_todo)
        self.delete_todo_btn.setEnabled(False)
        todo_header.addWidget(self.delete_todo_btn)
        
        todo_layout.addLayout(todo_header)
        
        # 列表
        self.todo_scroll = QScrollArea()
        self.todo_scroll.setWidgetResizable(True)
        self.todo_scroll.setFrameShape(QFrame.NoFrame)
        self.todo_scroll.setStyleSheet("background: transparent;") # 确保背景透明
        
        self.todo_container = QWidget()
        self.todo_container.setStyleSheet("background: transparent;") # 容器也透明
        self.todo_items_layout = QVBoxLayout(self.todo_container)
        self.todo_items_layout.setContentsMargins(0, 0, 0, 0)
        self.todo_items_layout.setSpacing(10)
        self.todo_items_layout.addStretch() # 底部弹簧，确保项目靠上
        
        self.todo_scroll.setWidget(self.todo_container)
        todo_layout.addWidget(self.todo_scroll)
        
        bottom_layout.addWidget(todo_frame, 1)  # 比例 1

        # 2. 便签
        notes_frame = QFrame()
        notes_frame.setProperty("class", "card")
        notes_layout = QVBoxLayout(notes_frame)
        
        # 标题栏
        notes_header = QHBoxLayout()
        notes_title = QLabel("便签")
        notes_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        notes_header.addWidget(notes_title)
        notes_header.addStretch()
        
        save_notes_btn = QPushButton("保存")
        save_notes_btn.setProperty("class", "primary small-btn")
        save_notes_btn.clicked.connect(self._save_notes)
        notes_header.addWidget(save_notes_btn)
        
        notes_layout.addLayout(notes_header)
        
        # 文本框
        self.notes_edit = QTextEdit()
        self.notes_edit.setFrameShape(QFrame.NoFrame)
        self.notes_edit.setPlaceholderText("在此输入便签内容...")
        notes_layout.addWidget(self.notes_edit)
        
        bottom_layout.addWidget(notes_frame, 1)  # 比例 1
        
        self.dashboard_layout.addLayout(bottom_layout)

    def _save_reminder_settings(self):
        """保存提醒设置"""
        self.settings.setValue("reminder_days", self.reminder_days.value())

    def _load_reminders(self):
        """加载到期提醒 (代理记账 + 合同)"""
        try:
            # 清空现有列表
            while self.reminder_layout.count():
                item = self.reminder_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            days = self.reminder_days.value()
            
            # 1. 获取代理记账到期
            expiring_businesses = self.db_manager.get_proxy_accounting_expiring(days)
            ignored_business_ids = self.settings.value("ignored_reminders", [], type=list)
            ignored_business_ids = [int(i) for i in ignored_business_ids]
            
            # 2. 获取合同到期
            expiring_contracts = self.db_manager.get_contracts_expiring(days)
            ignored_contract_ids = self.settings.value("ignored_contract_reminders", [], type=list)
            ignored_contract_ids = [int(i) for i in ignored_contract_ids]
            
            # 合并列表
            # item format: (id, name, date, type, raw_data)
            all_reminders = []
            
            for biz in expiring_businesses:
                if biz[0] not in ignored_business_ids:
                    all_reminders.append({
                        'id': biz[0],
                        'name': biz[1],
                        'date': biz[2],
                        'type': 'business',
                        'type_name': '记账'
                    })
                    
            for contract in expiring_contracts:
                if contract[0] not in ignored_contract_ids:
                    all_reminders.append({
                        'id': contract[0],
                        'name': contract[1],
                        'date': contract[2],
                        'type': 'contract',
                        'type_name': '合同'
                    })
            
            # 按日期排序
            all_reminders.sort(key=lambda x: x['date'])
            
            if not all_reminders:
                empty_label = QLabel("暂无即将到期的项目")
                empty_label.setAlignment(Qt.AlignCenter)
                # 仅设置 padding，颜色留给 QSS
                empty_label.setStyleSheet("padding: 20px;")
                self.reminder_layout.addWidget(empty_label)
                self.reminder_layout.addStretch()
                return
                
            today = QDate.currentDate()
            
            for item in all_reminders:
                end_date = QDate.fromString(item['date'], "yyyy-MM-dd")
                days_left = today.daysTo(end_date)
                
                if days_left < 0:
                    status_text = "已过期"
                    color_code = "#F56C6C" # Red
                elif days_left == 0:
                    status_text = "今天到期"
                    color_code = "#F56C6C" # Red
                else:
                    status_text = f"还有 {days_left} 天"
                    color_code = "#E6A23C" if days_left <= 7 else "#909399" # Orange or Gray
                
                # 创建行容器
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(10, 8, 10, 8)
                
                # 类型标签
                type_label = QLabel(f"[{item['type_name']}]")
                type_label.setStyleSheet("color: #409eff; font-weight: bold;")
                row_layout.addWidget(type_label)
                
                # 内容标签
                content_label = QLabel(
                    f"{item['name']} - {item['date']} "
                    f"<font color='{color_code}'><b>({status_text})</b></font>"
                )
                content_label.setTextFormat(Qt.RichText)
                content_label.setStyleSheet("background: transparent; font-size: 13px;")
                
                row_layout.addWidget(content_label)
                row_layout.addStretch() 
                
                # 设置行样式
                settings = QSettings("CustomerManagement", "Settings")
                is_dark = (settings.value("theme", "浅色") == "深色")
                hover_bg = "rgba(255, 255, 255, 0.1)" if is_dark else "#f5f7fa"
                border_color = "#444444" if is_dark else "#ebeef5"
                
                row_widget.setObjectName("reminderRow")
                row_widget.setStyleSheet(f"""
                    #reminderRow {{
                        border-bottom: 1px solid {border_color};
                    }}
                    #reminderRow:hover {{
                        background-color: {hover_bg};
                    }}
                """)
                
                # 启用右键菜单
                row_widget.setContextMenuPolicy(Qt.CustomContextMenu)
                row_widget.customContextMenuRequested.connect(
                    lambda pos, w=row_widget, i=item: self._show_reminder_context_menu(pos, w, i)
                )
                
                self.reminder_layout.addWidget(row_widget)
            
            # 添加底部弹簧
            self.reminder_layout.addStretch()
                
        except Exception as e:
            logger.error(f"Failed to load reminders: {e}")
            while self.reminder_layout.count():
                item = self.reminder_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            err_label = QLabel("加载失败")
            err_label.setStyleSheet("color: #F56C6C; padding: 20px;")
            self.reminder_layout.addWidget(err_label)
            self.reminder_layout.addStretch()

    def _show_reminder_context_menu(self, position, widget, item):
        """显示提醒列表右键菜单"""
        menu = QMenu()
        ignore_action = menu.addAction("忽略此提醒")
        
        # 将局部坐标转换为全局坐标
        global_pos = widget.mapToGlobal(position)
        action = menu.exec_(global_pos)
        
        if action == ignore_action:
            self._ignore_reminder(item['id'], item['type'])
    
    def _load_receivables(self):
        try:
            while self.receivable_items_layout.count():
                item = self.receivable_items_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            today = QDate.currentDate().toString('yyyy-MM-dd')
            next7 = QDate.currentDate().addDays(7).toString('yyyy-MM-dd')
            rows = []
            try:
                with self.db_manager.conn:
                    c = self.db_manager.conn.cursor()
                    c.execute('''
                        SELECT id, company_name, pending_amount, pending_date
                        FROM finance
                        WHERE pending_amount > 0 AND pending_date IS NOT NULL AND pending_date != ''
                        ORDER BY pending_date ASC
                    ''')
                    rows = c.fetchall()
            except Exception:
                rows = []
            items = []
            for r in rows:
                rid, name, amt, pdate = r
                if pdate < today or (pdate >= today and pdate <= next7):
                    items.append({'id': rid, 'name': name or '', 'amount': float(amt or 0), 'date': pdate})
            if not items:
                empty = QLabel("暂无近期应收账款")
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet("color: #909399; padding: 12px;")
                self.receivable_items_layout.addWidget(empty)
                self.receivable_items_layout.addStretch()
                return
            settings = QSettings("CustomerManagement", "Settings")
            is_dark = (settings.value("theme", "浅色") == "深色")
            hover_bg = "rgba(255, 255, 255, 0.1)" if is_dark else "#f5f7fa"
            border_color = "#444444" if is_dark else "#ebeef5"
            for it in items:
                w = QWidget()
                w.setObjectName("receivableRow")
                lay = QHBoxLayout(w)
                lay.setContentsMargins(12, 8, 12, 8)
                lay.setSpacing(10)
                name_label = QLabel(it['name'])
                name_label.setStyleSheet("background: transparent; font-size: 13px;")
                amt_label = QLabel(f"¥{it['amount']:.2f}")
                amt_label.setStyleSheet("font-weight: bold;")
                date_label = QLabel(it['date'])
                overdue = it['date'] < today
                if overdue:
                    date_label.setStyleSheet("color: #f56c6c;")
                    amt_label.setStyleSheet("font-weight: bold; color: #f56c6c;")
                else:
                    date_label.setStyleSheet("color: #e6a23c;")
                    amt_label.setStyleSheet("font-weight: bold; color: #e6a23c;")
                lay.addWidget(name_label, 1)
                lay.addWidget(date_label)
                lay.addWidget(amt_label)
                w.setStyleSheet(f"""
                    #receivableRow {{
                        border-bottom: 1px solid {border_color};
                    }}
                    #receivableRow:hover {{
                        background-color: {hover_bg};
                    }}
                """)
                
                # 双击跳转到财务记录
                def make_jump_handler(company_name):
                    def handler(event):
                        if self.main_window:
                            self.main_window.switch_to_finance()
                            self.main_window.btn_finance.setChecked(True)
                            if hasattr(self.main_window, 'finance'):
                                self.main_window.finance.search_and_select(company_name)
                    return handler
                
                w.mouseDoubleClickEvent = make_jump_handler(it['name'])
                w.setCursor(Qt.PointingHandCursor)
                w.setToolTip("双击查看详情")
                
                self.receivable_items_layout.addWidget(w)
            self.receivable_items_layout.addStretch()
        except Exception as e:
            while self.receivable_items_layout.count():
                item = self.receivable_items_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            err = QLabel("加载失败")
            err.setStyleSheet("color: #F56C6C; padding: 12px;")
            self.receivable_items_layout.addWidget(err)
            self.receivable_items_layout.addStretch()
            
    def _ignore_reminder(self, item_id, item_type):
        """忽略特定提醒"""
        try:
            key = "ignored_reminders" if item_type == "business" else "ignored_contract_reminders"
            ignored_ids = self.settings.value(key, [], type=list)
            ignored_ids = [int(i) for i in ignored_ids]
            
            if item_id not in ignored_ids:
                ignored_ids.append(item_id)
                self.settings.setValue(key, ignored_ids)
                
            # 刷新列表
            self._load_reminders()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"操作失败: {str(e)}")

    def update_data(self):
        # 从下拉框中获取日期
        start_date = QDate(
            int(self.start_year_combo.currentText()),
            int(self.start_month_combo.currentText()),
            int(self.start_day_combo.currentText())
        )
        end_date = QDate(
            int(self.end_year_combo.currentText()),
            int(self.end_month_combo.currentText()),
            int(self.end_day_combo.currentText())
        )
        """更新所有数据"""
        # 更新卡片数据
        self._update_cards()
        
        # 更新图表
        self.update_chart()
        self.update_distribution_chart()
        
        # 加载待办事项
        self._load_todos()
        
        # 加载到期提醒
        self._load_reminders()
        self._load_receivables()
        
        # 加载便签
        self._load_notes()

    def _update_cards(self):
        """更新卡片数据"""
        try:
            # 获取选择的日期范围
            start_date = QDate(
                int(self.start_year_combo.currentText()),
                int(self.start_month_combo.currentText()),
                int(self.start_day_combo.currentText())
            ).toString("yyyy-MM-dd")
            end_date = QDate(
                int(self.end_year_combo.currentText()),
                int(self.end_month_combo.currentText()),
                int(self.end_day_combo.currentText())
            ).toString("yyyy-MM-dd")
            
            # 从数据库获取数据
            stats = self.db_manager.get_dashboard_stats(start_date, end_date)
            
            # 单独获取总客户数(直接调用无参方法)
            total_customers = self.db_manager.get_customer_count()
            
            # 更新卡片显示
            # 查找卡片中的值标签并更新文本
            for card, value in zip(
                [self.total_customers_card, self.total_transactions_card, 
                 self.monthly_income_card, self.monthly_profit_card],
                [str(total_customers), str(stats['total_transactions']),
                 f"¥{stats['monthly_income']:,.2f}", f"¥{stats['monthly_profit']:,.2f}"]
            ):
                # 卡片布局中的第二个QLabel是值标签
                value_label = card.layout().itemAt(1).widget()
                value_label.setText(value)
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'获取统计数据失败: {str(e)}')

    def update_chart(self):
        """更新月度收支趋势图表"""
        try:
            # 更新图表主题
            self._update_chart_theme()
            
            year = int(self.year_combo.currentText())
            income_data = self.db_manager.get_monthly_income(year)
            expense_data = self.db_manager.get_monthly_expense_by_year(year)
            profit_data = self.db_manager.get_monthly_profit_by_year(year)
            
            self.monthly_chart.removeAllSeries()
            
            # 移除所有坐标轴，防止重复添加导致文字重叠
            for axis in self.monthly_chart.axes():
                self.monthly_chart.removeAxis(axis)
            
            if not income_data:  # 处理空数据情况
                self.monthly_chart.setTitle("无数据")
                return
                
            # 创建收入折线 (蓝色)
            income_series = QSplineSeries()
            income_series.setName("收入")
            income_series.setColor(QColor("#409eff")) 
            pen = income_series.pen()
            pen.setWidth(3)
            income_series.setPen(pen)
            
            # 创建支出折线 (红色)
            expense_series = QSplineSeries()
            expense_series.setName("支出")
            expense_series.setColor(QColor("#f56c6c"))
            pen = expense_series.pen()
            pen.setWidth(3)
            expense_series.setPen(pen)
            
            # 创建利润折线 (绿色)
            profit_series = QSplineSeries()
            profit_series.setName("利润")
            profit_series.setColor(QColor("#67c23a"))
            pen = profit_series.pen()
            pen.setWidth(3)
            profit_series.setPen(pen)
            
            months = []
            for i, (month, amount) in enumerate(income_data.items()):
                income_series.append(i, amount)
                expense_series.append(i, expense_data.get(month, 0))
                profit_series.append(i, profit_data.get(month, 0))
                months.append(month)
            
            # 添加系列到图表
            self.monthly_chart.addSeries(income_series)
            self.monthly_chart.addSeries(expense_series)
            self.monthly_chart.addSeries(profit_series)
            
            # 计算最大值以设置Y轴范围
            max_val = 0
            all_values = list(income_data.values()) + list(expense_data.values()) + list(profit_data.values())
            if all_values:
                max_val = max(all_values)
            
            # 设置X轴
            axisX = QBarCategoryAxis()
            axisX.append(months)
            self.monthly_chart.addAxis(axisX, Qt.AlignBottom)
            income_series.attachAxis(axisX)
            expense_series.attachAxis(axisX)
            profit_series.attachAxis(axisX)
            
            # 设置Y轴
            axisY = QValueAxis()
            axisY.setTitleText("金额 (元)")
            axisY.setRange(0, max_val * 1.2 if max_val > 0 else 100) # 增加20%的空间
            self.monthly_chart.addAxis(axisY, Qt.AlignLeft)
            income_series.attachAxis(axisY)
            expense_series.attachAxis(axisY)
            profit_series.attachAxis(axisY)
            
            # 显示图例
            self.monthly_chart.legend().setVisible(True)
            self.monthly_chart.legend().setAlignment(Qt.AlignBottom)
            
            self.monthly_chart.setTitle("")  # 清除无数据提示
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'获取图表数据失败: {str(e)}')

    def update_distribution_chart(self):
        """更新业务分布饼图"""
        try:
            # 更新主题
            self._update_chart_theme()
            
            self.pie_chart.removeAllSeries()
            self.pie_chart.setTitle("")
            
            distribution = self.db_manager.get_business_distribution()
            
            if not distribution:
                self.pie_chart.setTitle("暂无业务数据")
                return
                
            series = QPieSeries()
            
            # 计算总数以显示百分比
            total = sum(distribution.values())
            
            for business_type, count in distribution.items():
                if not business_type:
                    business_type = "未分类"
                slice_label = f"{business_type} ({count})"
                slice_item = series.append(slice_label, count)
                
                # 设置标签可见性
                slice_item.setLabelVisible(True)
                
            self.pie_chart.addSeries(series)
            
            # 突出显示最大的块
            # max_slice = max(series.slices(), key=lambda s: s.value())
            # max_slice.setExploded(True)
            # max_slice.setLabelVisible(True)
            
        except Exception as e:
            logger.error(f"Failed to update distribution chart: {e}")

    def _update_chart_theme(self):
        """更新图表主题"""
        # 重新读取设置，确保主题切换后立即生效
        settings = QSettings("CustomerManagement", "Settings")
        theme = settings.value("theme", "浅色", type=str)
        
        charts = [self.monthly_chart, self.pie_chart]
        
        for chart in charts:
            if theme == "深色":
                chart.setTheme(QChart.ChartThemeDark)
                chart.setBackgroundVisible(False) # 背景透明，使用卡片颜色
                
                # 设置坐标轴标签颜色为浅色
                for axis in chart.axes():
                    axis.setLabelsColor(QColor("#e0e0e0"))
                    axis.setTitleBrush(QColor("#e0e0e0"))
                    
                # 设置图例颜色
                chart.legend().setLabelColor(QColor("#e0e0e0"))
            else:
                chart.setTheme(QChart.ChartThemeLight)
                chart.setBackgroundVisible(True) # 浅色模式下显示图表自带的白色背景
                
                # 恢复坐标轴标签颜色
                for axis in chart.axes():
                    axis.setLabelsColor(QColor("#303133"))
                    axis.setTitleBrush(QColor("#303133"))
                    
                chart.legend().setLabelColor(QColor("#303133"))


    def _load_todos(self):
        """加载待办事项"""
        try:
            # 清除现有项目 (保留最后一个 stretch item)
            while self.todo_items_layout.count() > 1:
                item = self.todo_items_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            todos = self.db_manager.get_todos()
            
            # 用于存储选中的checkbox，以便更新删除按钮状态
            self.selected_todos = set()
            
            for todo in todos:
                widget = QWidget()
                widget.setProperty("class", "todo-item")
                # 样式移至QSS
                
                layout = QHBoxLayout(widget)
                layout.setContentsMargins(10, 8, 10, 8)
                layout.setSpacing(10)
                
                # 复选框
                checkbox = QCheckBox()
                checkbox.setChecked(todo['completed'])
                checkbox.stateChanged.connect(lambda state, id=todo['id']: 
                    self._update_todo_status(id, state == Qt.Checked))
                
                # 文本标签
                label = QLabel(todo['text'])
                label.setWordWrap(True)
                label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                # 设置最小高度确保文字不被截断
                label.setMinimumHeight(20) 
                
                if todo['completed']:
                    label.setStyleSheet("""
                        text-decoration: line-through; 
                        color: #909399;
                    """)
                else:
                    label.setProperty("class", "todo-text")
                    # color: #303133; 移至QSS
                
                # 点击事件处理 (模拟选中)
                # 注意：这里我们简化处理，点击checkbox旁边的区域也可以选中，
                # 但为了简单起见，我们主要通过复选框状态来控制
                
                # 选择框 (用于删除)
                select_check = QCheckBox()
                select_check.setToolTip("选中以删除")
                select_check.stateChanged.connect(lambda state, id=todo['id']: 
                    self._handle_todo_selection(id, state == Qt.Checked))
                
                layout.addWidget(checkbox)
                layout.addWidget(label, 1) # label占据主要空间
                layout.addWidget(select_check)
                
                # 插入到布局中 (stretch之前)
                self.todo_items_layout.insertWidget(self.todo_items_layout.count() - 1, widget)
                
            self._update_delete_button_state()
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载待办事项失败: {str(e)}')

    def _handle_todo_selection(self, todo_id, selected):
        """处理待办事项选中状态"""
        if selected:
            self.selected_todos.add(todo_id)
        else:
            self.selected_todos.discard(todo_id)
        self._update_delete_button_state()

    def _update_delete_button_state(self):
        """根据选中状态更新删除按钮"""
        self.delete_todo_btn.setEnabled(len(self.selected_todos) > 0)

    def _delete_selected_todo(self):
        """删除选中的待办事项"""
        if not self.selected_todos:
            return
            
        reply = QMessageBox.question(
            self, '确认删除',
            f'确定要删除选中的 {len(self.selected_todos)} 个待办事项吗?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                for todo_id in list(self.selected_todos):
                    self.db_manager.delete_todo(todo_id)
                self._load_todos()  # 刷新列表
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除待办事项失败: {str(e)}')

    def _delete_todo_item(self, todo_id):
        """删除指定ID的待办事项"""
        reply = QMessageBox.question(
            self, '确认删除',
            '确定要删除这个待办事项吗?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.delete_todo(todo_id)
                self._load_todos()  # 刷新列表
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除待办事项失败: {str(e)}')

    def _add_todo_item(self):
        """添加新待办事项"""
        text, ok = QInputDialog.getText(self, '添加待办', '输入待办事项内容:')
        if ok and text:
            try:
                self.db_manager.add_todo(text)
                self._load_todos()
            except Exception as e:
                QMessageBox.critical(self, '错误', f'添加待办事项失败: {str(e)}')

    def _update_todo_status(self, todo_id, completed):
        """更新待办事项状态"""
        try:
            self.db_manager.update_todo_status(todo_id, completed)
            self._load_todos()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'更新待办事项状态失败: {str(e)}')

    def _load_notes(self):
        """加载便签内容"""
        try:
            notes = self.db_manager.get_notes()
            self.notes_edit.setPlainText(notes)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'加载便签失败: {str(e)}')

    def _save_notes(self):
        """保存便签内容"""
        try:
            notes = self.notes_edit.toPlainText()
            self.db_manager.save_notes(notes)
            QMessageBox.information(self, '成功', '便签已保存')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存便签失败: {str(e)}')
            
    def refresh_stats(self):
        """刷新统计数据(供外部调用)"""
        self.update_data()

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QInputDialog
    import sys
    
    app = QApplication(sys.argv)
    window = DashboardWindow(None)
    window.show()
    sys.exit(app.exec_())
