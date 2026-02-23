from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QListWidget, QListWidgetItem, QDialog, QFormLayout, 
    QLineEdit, QTextEdit, QComboBox, QTimeEdit, QDateEdit,
    QMenu, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QDate, pyqtSignal, QSettings
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter
from datetime import datetime, timedelta
from modules.common_widgets import ModernDateEdit

class WorkCardWidget(QFrame):
    """工作安排卡片组件"""
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self._init_ui()
        
    def _init_ui(self):
        self.setObjectName("work-card")
        self.setProperty("priority", self.task_data['priority'])
        
        # 设置鼠标悬停提示 (Tooltip)
        tooltip_text = f"""<b>{self.task_data['title']}</b><br>
------------------------<br>
<b>时间:</b> {self.task_data['work_time']}<br>
<b>部门:</b> {self.task_data.get('department_name') or "无部门"}<br>
<b>详情:</b> {self.task_data.get('description', '无详情')}
"""
        self.setToolTip(tooltip_text)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel(self.task_data['title'])
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # 时间和部门
        info_layout = QHBoxLayout()
        time_str = self.task_data['work_time']
        time_label = QLabel(f"🕒 {time_str}")
        time_label.setProperty("class", "info-text")
        time_label.setStyleSheet("font-size: 12px;")
        
        dept_name = self.task_data.get('department_name') or "无部门"
        dept_label = QLabel(dept_name)
        dept_label.setStyleSheet("""
            padding: 2px 6px; 
            border-radius: 10px;
            font-size: 10px;
        """)
        
        info_layout.addWidget(time_label)
        info_layout.addStretch()
        info_layout.addWidget(dept_label)
        layout.addLayout(info_layout)
        
        # 设置样式 based on priority
        self._set_priority_style()
        
    def _set_priority_style(self):
        # 边框颜色已经在QSS中通过priority属性定义，这里可以额外设置背景等
        pass

class EmptyStateWidget(QWidget):
    """无数据时的占位显示"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter) # 顶对齐
        layout.setSpacing(10)
        layout.setContentsMargins(0, 20, 0, 0) # 顶部留出一些间距
        
        # 绘制纯灰色日历图标
        self.icon_label = QLabel()
        pixmap = self._draw_gray_calendar_icon()
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # 文字
        text_label = QLabel("暂无工作安排")
        text_label.setStyleSheet("color: #999999; font-size: 13px;")
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)
        
    def update_theme(self):
        """更新主题样式"""
        pixmap = self._draw_gray_calendar_icon()
        self.icon_label.setPixmap(pixmap)
        
    def _draw_gray_calendar_icon(self):
        """绘制一个简单的灰色日历图标"""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 颜色
        settings = QSettings("CustomerManagement", "Settings")
        is_dark = (settings.value("theme", "浅色") == "深色")
        
        if is_dark:
            bg_color = QColor("#404040")  # 深色模式：深灰底
            border_color = QColor("#555555") 
            header_color = QColor("#252525") # 深色模式：头部更深
            dot_color = QColor("#666666")    # 深色模式：点
        else:
            bg_color = QColor("#f0f0f0")  # 浅灰底
            border_color = QColor("#d0d0d0") # 边框
            header_color = QColor("#b0b0b0") # 头部深灰
            dot_color = QColor("#d0d0d0") # 点
        
        # 绘制主体
        rect = pixmap.rect().adjusted(4, 4, -4, -4)
        
        # 背景
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, 8, 8)
        
        # 头部
        header_height = 16
        header_rect = list(rect.getRect())
        header_rect[3] = header_height
        
        path = painter.clipPath()
        painter.setBrush(header_color)
        # 只绘制上半部分的圆角需要一些技巧，这里简单绘制覆盖
        painter.drawRoundedRect(rect.x(), rect.y(), rect.width(), header_height + 8, 8, 8)
        # 恢复下半部分为背景色 (遮盖圆角) - 其实可以直接画一个矩形
        painter.setBrush(bg_color)
        painter.drawRect(rect.x(), rect.y() + header_height, rect.width(), rect.height() - header_height - 8)
        # 重新绘制底部圆角背景
        painter.drawRoundedRect(rect.x(), rect.y() + header_height, rect.width(), rect.height() - header_height, 8, 8)
        
        # 重新绘制头部 (确保顶部圆角)
        painter.setBrush(header_color)
        painter.drawRoundedRect(rect.x(), rect.y(), rect.width(), header_height * 2, 8, 8) # 先画大的
        # 切掉下半部分
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.setBrush(bg_color)
        painter.drawRect(rect.x(), rect.y() + header_height, rect.width(), rect.height() - header_height)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        
        # 模拟日历格子
        painter.setBrush(dot_color)
        grid_y = rect.y() + header_height + 8
        grid_w = 6
        grid_gap = 6
        start_x = rect.x() + 10
        
        for row in range(2):
            for col in range(3):
                px = start_x + col * (grid_w + grid_gap)
                py = grid_y + row * (grid_w + grid_gap)
                painter.drawEllipse(px, py, grid_w, grid_w)
        
        painter.end()
        return pixmap

class TaskDialog(QDialog):
    """添加/编辑任务对话框"""
    def __init__(self, db_manager, task_data=None, default_date=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.task_data = task_data
        self.default_date = default_date
        self.setWindowTitle("编辑工作安排" if task_data else "新建工作安排")
        self.setFixedWidth(400)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # 标题
        self.title_input = QLineEdit()
        if self.task_data:
            self.title_input.setText(self.task_data['title'])
        form_layout.addRow("标题:", self.title_input)
        
        # 内容
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(100)
        if self.task_data:
            self.desc_input.setText(self.task_data.get('description', ''))
        form_layout.addRow("详情:", self.desc_input)
        
        # 日期
        self.date_input = ModernDateEdit()
        if self.task_data:
            self.date_input.setDate(QDate.fromString(self.task_data['work_date'], "yyyy-MM-dd"))
        elif self.default_date:
            self.date_input.setDate(self.default_date)
        else:
            self.date_input.setDate(QDate.currentDate())
        form_layout.addRow("日期:", self.date_input)
        
        # 时间
        self.time_input = QTimeEdit()
        if self.task_data:
            self.time_input.setTime(datetime.strptime(self.task_data['work_time'], "%H:%M").time())
        else:
            self.time_input.setTime(datetime.now().time())
        form_layout.addRow("时间:", self.time_input)
        
        # 部门
        self.dept_combo = QComboBox()
        self._load_departments()
        if self.task_data and self.task_data.get('department_id'):
            index = self.dept_combo.findData(self.task_data['department_id'])
            if index >= 0:
                self.dept_combo.setCurrentIndex(index)
        form_layout.addRow("部门:", self.dept_combo)
        
        # 优先级
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("普通", "medium")
        self.priority_combo.addItem("紧急", "high")
        self.priority_combo.addItem("较低", "low")
        if self.task_data:
            index = self.priority_combo.findData(self.task_data['priority'])
            if index >= 0:
                self.priority_combo.setCurrentIndex(index)
        form_layout.addRow("优先级:", self.priority_combo)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        save_btn.setStyleSheet("background-color: #06d6a0; color: white;")
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
    def _load_departments(self):
        departments = self.db_manager.execute_query("SELECT id, name FROM departments ORDER BY name")
        self.dept_combo.addItem("无部门", None)
        for dept in departments:
            self.dept_combo.addItem(dept[1], dept[0])
            
    def get_data(self):
        return {
            'title': self.title_input.text().strip(),
            'description': self.desc_input.toPlainText(),
            'work_date': self.date_input.date().toString("yyyy-MM-dd"),
            'work_time': self.time_input.time().toString("HH:mm"),
            'department_id': self.dept_combo.currentData(),
            'priority': self.priority_combo.currentData()
        }

class DepartmentDialog(QDialog):
    """部门管理对话框"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("部门管理")
        self.setFixedSize(400, 500)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 添加部门
        add_layout = QHBoxLayout()
        self.new_dept_input = QLineEdit()
        self.new_dept_input.setPlaceholderText("输入新部门名称")
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_department)
        add_layout.addWidget(self.new_dept_input)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)
        
        # 部门列表
        self.dept_list = QListWidget()
        layout.addWidget(self.dept_list)
        
        # 删除按钮
        del_btn = QPushButton("删除选中部门")
        del_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
        del_btn.clicked.connect(self._delete_department)
        layout.addWidget(del_btn)
        
        self._load_departments()
        
    def _load_departments(self):
        self.dept_list.clear()
        departments = self.db_manager.execute_query("SELECT id, name FROM departments ORDER BY created_at DESC")
        for dept in departments:
            item = QListWidgetItem(dept[1])
            item.setData(Qt.UserRole, dept[0])
            self.dept_list.addItem(item)
            
    def _add_department(self):
        name = self.new_dept_input.text().strip()
        if not name:
            return
            
        try:
            self.db_manager.execute_query(
                "INSERT INTO departments (name) VALUES (?)", 
                (name,), fetch=False
            )
            self.db_manager.conn.commit()
            self._load_departments()
            self.new_dept_input.clear()
            self._log_action("create_dept", f"创建部门: {name}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"添加失败: {str(e)}")
            
    def _delete_department(self):
        item = self.dept_list.currentItem()
        if not item:
            return
            
        dept_id = item.data(Qt.UserRole)
        name = item.text()
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除部门 '{name}' 吗？\n相关工作安排将变为'无部门'。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query(
                    "DELETE FROM departments WHERE id = ?", 
                    (dept_id,), fetch=False
                )
                self.db_manager.conn.commit()
                self._load_departments()
                self._log_action("delete_dept", f"删除部门: {name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {str(e)}")

    def _log_action(self, action, details):
        try:
            self.db_manager.execute_query(
                "INSERT INTO work_logs (action, details) VALUES (?, ?)",
                (action, details), fetch=False
            )
            self.db_manager.conn.commit()
        except:
            pass

class LogDialog(QDialog):
    """日志查询对话框"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("操作日志")
        self.resize(600, 400)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["时间", "操作", "详情"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        
        self._load_logs()
        
    def _load_logs(self):
        logs = self.db_manager.execute_query(
            "SELECT created_at, action, details FROM work_logs ORDER BY created_at DESC LIMIT 100"
        )
        self.table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table.setItem(i, 0, QTableWidgetItem(str(log[0])))
            self.table.setItem(i, 1, QTableWidgetItem(str(log[1])))
            self.table.setItem(i, 2, QTableWidgetItem(str(log[2])))

class WorkSearchDialog(QDialog):
    """工作安排搜索对话框"""
    def __init__(self, db_manager, query, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.query = query
        self.setWindowTitle(f"搜索结果 - '{query}'")
        self.resize(600, 400)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["日期", "标题", "详情"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        
        self._perform_search()
        
    def _perform_search(self):
        try:
            keyword = f"%{self.query}%"
            # 搜索标题或详情
            sql = """
                SELECT work_date, title, description 
                FROM work_arrangements 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY work_date DESC
            """
            cursor = self.db_manager.conn.cursor()
            cursor.execute(sql, (keyword, keyword))
            results = cursor.fetchall()
            
            self.table.setRowCount(len(results))
            for i, row in enumerate(results):
                self.table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))
                self.table.setItem(i, 2, QTableWidgetItem(str(row[2])))
                
            if not results:
                QMessageBox.information(self, "提示", "未找到相关工作安排")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")

class WorkArrangementWindow(QWidget):
    """工作安排主窗口"""
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_start_date = self._get_start_of_week(QDate.currentDate())
        self.day_lists = [] # 存储7天的QListWidget
        self._init_ui()
        
    def _get_start_of_week(self, date):
        # 获取周一
        return date.addDays(-(date.dayOfWeek() - 1))
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部导航栏
        nav_layout = QHBoxLayout()
        
        prev_btn = QPushButton("◀ 上周")
        prev_btn.clicked.connect(self._prev_week)
        self.date_range_label = QLabel()
        self.date_range_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        # Remove Expanding policy to keep buttons together
        # self.date_range_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.date_range_label.setWordWrap(False)
        next_btn = QPushButton("下周 ▶")
        next_btn.clicked.connect(self._next_week)
        
        nav_layout.addWidget(prev_btn)
        nav_layout.addSpacing(20)
        nav_layout.addWidget(self.date_range_label)
        nav_layout.addSpacing(20)
        nav_layout.addWidget(next_btn)
        nav_layout.addStretch()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索关键词...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self._search_work)
        nav_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self._search_work)
        search_btn.setStyleSheet("background-color: #409eff; color: white;")
        nav_layout.addWidget(search_btn)
        
        nav_layout.addSpacing(10)
        
        # 功能按钮
        manage_dept_btn = QPushButton("管理部门")
        manage_dept_btn.clicked.connect(self._open_manage_depts)
        manage_dept_btn.setStyleSheet("background-color: #5d8bf4; color: white;")
        
        logs_btn = QPushButton("日志查询")
        logs_btn.clicked.connect(self._open_logs)
        logs_btn.setStyleSheet("background-color: #ffd166; color: #333;")
        
        nav_layout.addWidget(manage_dept_btn)
        nav_layout.addWidget(logs_btn)
        
        layout.addLayout(nav_layout)
        
        # 周视图
        week_layout = QHBoxLayout()
        week_layout.setSpacing(10)
        
        week_days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        for i in range(7):
            day_container = QFrame()
            day_container.setObjectName("day-container")
            day_layout = QVBoxLayout(day_container)
            day_layout.setContentsMargins(0, 0, 0, 0)
            
            # 标题头
            header = QLabel(week_days[i])
            header.setObjectName(f"day-header-{i}")
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet("""
                background-color: #5d8bf4;
                color: white;
                padding: 10px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            """)
            day_layout.addWidget(header)
            
            # 列表
            list_widget = QListWidget()
            list_widget.setFrameShape(QFrame.NoFrame)
            list_widget.setStyleSheet("background-color: transparent;")
            list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            list_widget.customContextMenuRequested.connect(lambda pos, lw=list_widget: self._show_context_menu(pos, lw))
            list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
            
            # 存储引用以便后续使用
            list_widget.day_index = i 
            
            day_layout.addWidget(list_widget)
            
            # 空状态组件
            empty_widget = EmptyStateWidget()
            empty_widget.hide()
            # 允许右键点击空状态区域
            empty_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            empty_widget.customContextMenuRequested.connect(lambda pos, idx=i: self._show_empty_context_menu(pos, idx))
            day_layout.addWidget(empty_widget)
            
            # 添加按钮
            add_btn = QPushButton("+ 添加安排")
            add_btn.setStyleSheet("""
                border: none;
                color: #5d8bf4;
                padding: 8px;
                text-align: center;
            """)
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.clicked.connect(lambda checked, idx=i: self._open_add_dialog(day_index=idx))
            day_layout.addWidget(add_btn)
            
            week_layout.addWidget(day_container, 1)
            self.day_lists.append({
                'header': header,
                'list': list_widget,
                'container': day_container,
                'empty': empty_widget
            })
            
        layout.addLayout(week_layout)
        
        self._refresh_view()
    
    def _update_date_range_label(self):
        try:
            if not hasattr(self, 'date_range_label'):
                return
            full_text = getattr(self, '_full_date_range_text', '')
            if not full_text:
                return
            fm = self.date_range_label.fontMetrics()
            width = max(10, self.date_range_label.width())
            elided = fm.elidedText(full_text, Qt.ElideRight, width)
            self.date_range_label.setText(elided)
            self.date_range_label.setToolTip(full_text)
        except Exception:
            pass
        
    def _refresh_view(self):
        # 更新日期显示
        end_date = self.current_start_date.addDays(6)
        self._full_date_range_text = f"{self.current_start_date.toString('yyyy年MM月dd日')} - {end_date.toString('MM月dd日')}"
        self._update_date_range_label()
        
        # 清空列表
        for day in self.day_lists:
            day['list'].clear()
            
        # 获取本周数据
        start_str = self.current_start_date.toString("yyyy-MM-dd")
        end_str = end_date.toString("yyyy-MM-dd")
        
        query = """
            SELECT w.id, w.title, w.description, w.work_date, w.work_time, 
                   w.department_id, w.priority, w.status, d.name as department_name
            FROM work_arrangements w
            LEFT JOIN departments d ON w.department_id = d.id
            WHERE w.work_date BETWEEN ? AND ?
            ORDER BY w.work_time ASC
        """
        
        tasks = self.db_manager.execute_query(query, (start_str, end_str))
        
        # 分类填充
        today = QDate.currentDate()
        
        for i in range(7):
            current_day_date = self.current_start_date.addDays(i)
            day_tasks = [t for t in tasks if t[3] == current_day_date.toString("yyyy-MM-dd")]
            
            # 控制空状态显示
            if not day_tasks:
                self.day_lists[i]['list'].hide()
                self.day_lists[i]['empty'].show()
            else:
                self.day_lists[i]['list'].show()
                self.day_lists[i]['empty'].hide()
            
            # 高亮今天
            header = self.day_lists[i]['header']
            if current_day_date == today:
                header.setStyleSheet("""
                    background-color: #ff6b6b;
                    color: white;
                    padding: 10px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: bold;
                """)
                header.setText(f"{['周一','周二','周三','周四','周五','周六','周日'][i]} (今天)")
            else:
                header.setStyleSheet("""
                    background-color: #5d8bf4;
                    color: white;
                    padding: 10px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: bold;
                """)
                header.setText(f"{['周一','周二','周三','周四','周五','周六','周日'][i]} {current_day_date.toString('MM/dd')}")
            
            for task in day_tasks:
                task_dict = {
                    'id': task[0],
                    'title': task[1],
                    'description': task[2],
                    'work_date': task[3],
                    'work_time': task[4],
                    'department_id': task[5],
                    'priority': task[6],
                    'status': task[7],
                    'department_name': task[8]
                }
                
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 80))
                # 存储数据
                item.setData(Qt.UserRole, task_dict)
                
                card = WorkCardWidget(task_dict)
                self.day_lists[i]['list'].addItem(item)
                self.day_lists[i]['list'].setItemWidget(item, card)

    def update_theme(self):
        """更新主题"""
        for day in self.day_lists:
            if day['empty']:
                day['empty'].update_theme()

    def _prev_week(self):
        self.current_start_date = self.current_start_date.addDays(-7)
        self._refresh_view()
        
    def _next_week(self):
        self.current_start_date = self.current_start_date.addDays(7)
        self._refresh_view()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_date_range_label()
        
    def _open_add_dialog(self, day_index=None):
        default_date = None
        if day_index is not None:
            default_date = self.current_start_date.addDays(day_index)
            
        dialog = TaskDialog(self.db_manager, default_date=default_date, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.db_manager.execute_query(
                    """INSERT INTO work_arrangements 
                       (title, description, work_date, work_time, department_id, priority) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (data['title'], data['description'], data['work_date'], 
                     data['work_time'], data['department_id'], data['priority']),
                    fetch=False
                )
                self.db_manager.conn.commit()
                self._log_action("create_task", f"创建任务: {data['title']}")
                self._refresh_view()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")
                
    def _on_item_double_clicked(self, item):
        task_data = item.data(Qt.UserRole)
        dialog = TaskDialog(self.db_manager, task_data=task_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.db_manager.execute_query(
                    """UPDATE work_arrangements 
                       SET title=?, description=?, work_date=?, work_time=?, 
                           department_id=?, priority=?
                       WHERE id=?""",
                    (data['title'], data['description'], data['work_date'], 
                     data['work_time'], data['department_id'], data['priority'], 
                     task_data['id']),
                    fetch=False
                )
                self.db_manager.conn.commit()
                self._log_action("update_task", f"更新任务: {data['title']}")
                self._refresh_view()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"更新失败: {str(e)}")

    def _show_context_menu(self, pos, list_widget):
        item = list_widget.itemAt(pos)
        menu = QMenu()
        
        if item:
            # 选中了任务
            task_data = item.data(Qt.UserRole)
            edit_action = menu.addAction("编辑")
            delete_action = menu.addAction("取消/删除")
            menu.addSeparator()
            
            add_action = menu.addAction("添加安排")
            
            action = menu.exec_(list_widget.mapToGlobal(pos))
            
            if action == edit_action:
                self._on_item_double_clicked(item)
            elif action == delete_action:
                self._delete_task(task_data)
            elif action == add_action:
                self._open_add_dialog(day_index=list_widget.day_index)
        else:
            # 点击了空白处
            add_action = menu.addAction("添加安排")
            action = menu.exec_(list_widget.mapToGlobal(pos))
            
            if action == add_action:
                self._open_add_dialog(day_index=list_widget.day_index)

    def _show_empty_context_menu(self, pos, day_index):
        """空状态组件的右键菜单"""
        menu = QMenu()
        add_action = menu.addAction("添加安排")
        
        # 获取触发事件的组件（sender），用于定位菜单显示位置
        sender_widget = self.sender() 
        # 注意：在lambda中sender()可能不准确，最好直接用pos映射
        # 但这里sender是empty_widget，pos是相对sender的
        # 为了保险，我们通过day_lists找到对应的empty_widget
        empty_widget = self.day_lists[day_index]['empty']
        
        action = menu.exec_(empty_widget.mapToGlobal(pos))
        
        if action == add_action:
            self._open_add_dialog(day_index=day_index)
            
    def _delete_task(self, task_data):
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除任务 '{task_data['title']}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query(
                    "DELETE FROM work_arrangements WHERE id = ?",
                    (task_data['id'],), fetch=False
                )
                self.db_manager.conn.commit()
                self._log_action("delete_task", f"删除任务: {task_data['title']}")
                self._refresh_view()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败: {str(e)}")

    def _open_manage_depts(self):
        dialog = DepartmentDialog(self.db_manager, self)
        dialog.exec_()
        self._refresh_view() # 刷新以更新部门显示
        
    def _open_logs(self):
        dialog = LogDialog(self.db_manager, self)
        dialog.exec_()

    def _search_work(self):
        query = self.search_input.text().strip()
        if not query:
            return
            
        dialog = WorkSearchDialog(self.db_manager, query, self)
        dialog.exec_()

    def _log_action(self, action, details):
        try:
            self.db_manager.execute_query(
                "INSERT INTO work_logs (action, details) VALUES (?, ?)",
                (action, details), fetch=False
            )
            self.db_manager.conn.commit()
        except:
            pass
