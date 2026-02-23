import os
import math
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QSplitter, QGroupBox, QRadioButton, QComboBox, 
    QSpinBox, QCheckBox, QLineEdit, QListWidget, QListWidgetItem,
    QGridLayout, QSizePolicy, QFileDialog, QMessageBox, QProgressDialog,
    QAbstractItemView, QScrollArea
)
from PyQt5.QtCore import Qt, QSize, QUrl, QStandardPaths, pyqtSignal, QRectF
from PyQt5.QtGui import QIcon, QColor, QPalette, QPainter, QImage, QDesktopServices, QPixmap
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from core.logger import logger

CONFIG_FILE = "invoice_config.json"

class DropLabel(QLabel):
    """支持拖拽的标签"""
    file_dropped = pyqtSignal(list)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("color: #909399; font-size: 14px; border: 2px dashed #dcdfe6; border-radius: 4px;")
        # Ensure it expands to fill the space
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
            self.file_dropped.emit(files)
        else:
            super().dropEvent(event)

class PreviewWidget(QWidget):
    """实时预览控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setMinimumSize(300, 400)
        self.setStyleSheet("background-color: #525659;") # PDF 阅读器常见背景色

    def update_image(self, image):
        self.image = image
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor("#525659"))
        
        if self.image:
            # 计算居中显示
            # 保持比例缩放
            if self.image.width() > 0 and self.image.height() > 0:
                scale = min(self.width() / self.image.width(), self.height() / self.image.height())
                scale = min(scale, 1.0) # 不放大
                
                # 留一点边距
                display_width = int(self.image.width() * scale * 0.95)
                display_height = int(self.image.height() * scale * 0.95)
                
                x = (self.width() - display_width) // 2
                y = (self.height() - display_height) // 2
                
                target_rect = QRectF(x, y, display_width, display_height)
                painter.drawImage(target_rect, self.image, QRectF(self.image.rect()))
        else:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "预览区域")

class FileDropListWidget(QListWidget):
    """支持文件拖拽的列表控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Allow DragDrop to support both internal reordering and external drops
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        # Check if it's an internal move
        if event.source() == self:
            super().dropEvent(event)
        elif event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
            # Call parent method to add files
            if self.parent():
                self.parent().add_files_from_drop(files)
        else:
            super().dropEvent(event)

class InvoiceSystemWindow(QWidget):
    """发票系统主窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_preview_page = 0
        self.total_preview_pages = 0
        self.image_cache = {} # Cache for rendered file thumbnails (file_path -> QImage)
        self._init_ui()
        self._load_config()
        
    def add_files_from_drop(self, files):
        """处理拖拽添加的文件"""
        added_count = 0
        for file_path in files:
            # 简单过滤图片和PDF
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.pdf']:
                # Avoid duplicates? Optional. For now allow.
                self.file_list.addItem(file_path)
                added_count += 1
        
        if added_count > 0:
            self._update_file_count()
            self._update_preview()
        else:
            QMessageBox.information(self, "提示", "仅支持添加图片或PDF文件")

    def _init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20) # Increased spacing to match dashboard
        
        # 1. 顶部工具栏 (打印、导出)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        
        # REMOVED Print Button
        
        self.btn_export = QPushButton("合并导出") # Renamed from 导出
        self.btn_export.setFixedSize(100, 32)
        self.btn_export.setProperty("class", "success")
        
        top_bar.addWidget(self.btn_export)
        main_layout.addLayout(top_bar)
        
        # 2. 中间内容区 (左右分栏)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)
        
        # 左侧：文件列表
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # 左侧头部
        left_header = QHBoxLayout()
        self.file_count_label = QLabel("文件 0")
        self.file_count_label.setStyleSheet("font-weight: bold;")
        left_header.addWidget(self.file_count_label)
        left_header.addStretch()
        
        btn_add = QPushButton("添加")
        # REMOVED Identify Button
        btn_clear = QPushButton("清空")
        
        for btn in [btn_add, btn_clear]:
            btn.setFixedSize(60, 32)
            left_header.addWidget(btn)
            
        left_layout.addLayout(left_header)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文件名或路径...")
        left_layout.addWidget(self.search_input)
        
        # 拖拽区域/列表容器
        list_container = QFrame()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.file_list = FileDropListWidget(self)
        self.file_list.setAlternatingRowColors(True)
        
        self.drop_area_label = DropLabel("点击\"添加\"或拖放文件到此处导入")
        self.drop_area_label.file_dropped.connect(self.add_files_from_drop)
        
        list_layout.addWidget(self.drop_area_label)
        list_layout.addWidget(self.file_list)
        self.file_list.hide() # 初始隐藏列表
        
        left_layout.addWidget(list_container)
        
        # 右侧：预览区
        right_panel = QFrame()
        right_panel.setProperty("class", "card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # 预览区头部 (包含分页导航)
        right_header = QHBoxLayout()
        right_header_label = QLabel("预览 合并预览")
        right_header_label.setStyleSheet("font-weight: bold;")
        right_header.addWidget(right_header_label)
        
        right_header.addStretch()
        
        # 分页控件
        self.btn_prev_page = QPushButton("<")
        self.btn_prev_page.setFixedSize(32, 32)
        self.btn_prev_page.setCursor(Qt.PointingHandCursor)
        self.btn_prev_page.clicked.connect(self._prev_page)
        
        self.label_page_info = QLabel("0 / 0")
        self.label_page_info.setStyleSheet("color: #606266; margin: 0 10px;")
        
        self.btn_next_page = QPushButton(">")
        self.btn_next_page.setFixedSize(32, 32)
        self.btn_next_page.setCursor(Qt.PointingHandCursor)
        self.btn_next_page.clicked.connect(self._next_page)
        
        right_header.addWidget(self.btn_prev_page)
        right_header.addWidget(self.label_page_info)
        right_header.addWidget(self.btn_next_page)
        
        right_layout.addLayout(right_header)
        
        self.preview_area = PreviewWidget()
        right_layout.addWidget(self.preview_area, 1) # Add stretch factor 1 to expand preview area
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1) # 左侧比例
        splitter.setStretchFactor(1, 2) # 右侧比例大一点
        
        main_layout.addWidget(splitter, 1) # 伸缩因子1，占据主要空间
        
        # 3. 底部配置区
        bottom_panel = QFrame()
        bottom_panel.setProperty("class", "card")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(15, 15, 15, 15)
        
        # 底部标题栏
        bottom_header = QHBoxLayout()
        bottom_title = QLabel("预览配置")
        bottom_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        bottom_header.addWidget(bottom_title)
        bottom_header.addStretch()
        
        self.btn_config = QPushButton("保存配置")
        # REMOVED Config Identify Button
        for btn in [self.btn_config]:
            btn.setFixedSize(70, 32)
            bottom_header.addWidget(btn)
            
        bottom_layout.addLayout(bottom_header)
        
        # 配置选项区域
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)
        
        # 布局选项
        layout_group = QGroupBox("布局选项")
        layout_grid = QGridLayout(layout_group)
        
        self.rb_2_per_page = QRadioButton("每页2张")
        self.rb_3_per_page = QRadioButton("每页3张")
        self.rb_4_per_page = QRadioButton("每页4张")
        self.rb_6_per_page = QRadioButton("每页6张")
        self.rb_hsr = QRadioButton("高铁票布局")
        self.rb_hsr.setChecked(True)
        
        for rb in [self.rb_2_per_page, self.rb_3_per_page, self.rb_4_per_page, self.rb_6_per_page, self.rb_hsr]:
            rb.toggled.connect(self._reset_page_and_update)
            
        layout_grid.addWidget(self.rb_2_per_page, 0, 0)
        layout_grid.addWidget(self.rb_3_per_page, 0, 1)
        layout_grid.addWidget(self.rb_4_per_page, 1, 0)
        layout_grid.addWidget(self.rb_6_per_page, 1, 1)
        layout_grid.addWidget(self.rb_hsr, 2, 0, 1, 2)
        
        options_layout.addWidget(layout_group)
        
        # 纸张设置
        paper_group = QGroupBox("纸张设置")
        paper_layout = QGridLayout(paper_group)
        
        paper_layout.addWidget(QLabel("尺寸"), 0, 0)
        paper_layout.addWidget(QLabel("纸张方向"), 0, 1)
        
        self.combo_size = QComboBox()
        self.combo_size.addItems(["A4", "A5", "Letter"])
        self.combo_size.currentIndexChanged.connect(self._update_preview)
        paper_layout.addWidget(self.combo_size, 1, 0)
        
        self.combo_orient = QComboBox()
        self.combo_orient.addItems(["纵向", "横向"])
        self.combo_orient.currentIndexChanged.connect(self._update_preview)
        paper_layout.addWidget(self.combo_orient, 1, 1)
        
        paper_layout.addWidget(QLabel("自定义 (mm)"), 2, 0, 1, 2)
        custom_size_layout = QHBoxLayout()
        self.spin_width = QSpinBox()
        self.spin_width.setValue(210)
        self.spin_width.setRange(0, 9999)
        self.spin_width.valueChanged.connect(self._update_preview)
        self.spin_height = QSpinBox()
        self.spin_height.setValue(297)
        self.spin_height.setRange(0, 9999)
        self.spin_height.valueChanged.connect(self._update_preview)
        
        custom_size_layout.addWidget(self.spin_width)
        custom_size_layout.addWidget(QLabel("x"))
        custom_size_layout.addWidget(self.spin_height)
        paper_layout.addLayout(custom_size_layout, 3, 0, 1, 2)
        
        # 边距
        paper_layout.addWidget(QLabel("边距 (mm)"), 0, 2, 1, 2)
        margin_grid = QGridLayout()
        self.margin_top = QSpinBox()
        self.margin_top.setValue(12)
        self.margin_right = QSpinBox()
        self.margin_right.setValue(12)
        self.margin_bottom = QSpinBox()
        self.margin_bottom.setValue(12)
        self.margin_left = QSpinBox()
        self.margin_left.setValue(12)
        
        for spin in [self.margin_top, self.margin_right, self.margin_bottom, self.margin_left]:
            spin.setFixedWidth(60)
            spin.valueChanged.connect(self._update_preview)
            
        margin_grid.addWidget(QLabel("上"), 0, 0)
        margin_grid.addWidget(self.margin_top, 0, 1)
        margin_grid.addWidget(QLabel("右"), 0, 2)
        margin_grid.addWidget(self.margin_right, 0, 3)
        margin_grid.addWidget(QLabel("下"), 1, 0)
        margin_grid.addWidget(self.margin_bottom, 1, 1)
        margin_grid.addWidget(QLabel("左"), 1, 2)
        margin_grid.addWidget(self.margin_left, 1, 3)
        
        paper_layout.addLayout(margin_grid, 1, 2, 3, 2)
        
        options_layout.addWidget(paper_group)
        
        # 其他选项
        other_group = QGroupBox("其他选项")
        other_layout = QGridLayout(other_group)
        
        self.switch_merge = QCheckBox("合并预览")
        self.switch_merge.setChecked(True)
        self.switch_merge.toggled.connect(self._reset_page_and_update)
        self.switch_cut = QCheckBox("裁剪线")
        self.switch_cut.setChecked(True)
        self.switch_cut.toggled.connect(self._update_preview)
        
        other_layout.addWidget(self.switch_merge, 0, 0)
        other_layout.addWidget(self.switch_cut, 0, 1)
        
        # 装订孔位
        self.check_binding_hole = QCheckBox("装订孔位")
        self.check_binding_hole.toggled.connect(self._update_preview)
        other_layout.addWidget(self.check_binding_hole, 1, 0)
        
        self.combo_hole_pos = QComboBox()
        self.combo_hole_pos.addItems(["左侧", "顶部"])
        self.combo_hole_pos.currentIndexChanged.connect(self._update_preview)
        other_layout.addWidget(self.combo_hole_pos, 1, 1)
        
        self.combo_hole_count = QComboBox()
        self.combo_hole_count.addItems(["2孔", "3孔", "4孔"])
        self.combo_hole_count.currentIndexChanged.connect(self._update_preview)
        other_layout.addWidget(self.combo_hole_count, 1, 2)
        
        # 装订线条
        self.check_binding_line = QCheckBox("装订线条")
        self.check_binding_line.toggled.connect(self._update_preview)
        other_layout.addWidget(self.check_binding_line, 2, 0)
        
        self.combo_line_pos = QComboBox()
        self.combo_line_pos.addItems(["左侧", "顶部"])
        self.combo_line_pos.currentIndexChanged.connect(self._update_preview)
        other_layout.addWidget(self.combo_line_pos, 2, 1)
        
        self.combo_line_style = QComboBox()
        self.combo_line_style.addItems(["虚线", "实线"])
        self.combo_line_style.currentIndexChanged.connect(self._update_preview)
        other_layout.addWidget(self.combo_line_style, 2, 2)
        
        # 重置配置按钮
        self.btn_reset = QPushButton("重置配置")
        other_layout.addWidget(self.btn_reset, 3, 0, 1, 3)
        
        options_layout.addWidget(other_group)
        
        bottom_layout.addLayout(options_layout)
        
        main_layout.addWidget(bottom_panel)
        
        # Connect signals
        btn_add.clicked.connect(self._add_files)
        btn_clear.clicked.connect(self._clear_files)
        # REMOVED Identify connections
        self.btn_export.clicked.connect(self._handle_export)
        self.btn_config.clicked.connect(self._save_config)
        self.btn_reset.clicked.connect(self._reset_config)
    
    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", "Images (*.png *.jpg *.jpeg *.bmp *.pdf);;All Files (*)")
        if files:
            for file in files:
                self.file_list.addItem(file)
            self._update_file_count()
            self._update_preview()
            
    def _update_file_count(self):
        count = self.file_list.count()
        self.file_count_label.setText(f"文件 {count}")
        if count > 0:
            self.file_list.show()
            self.drop_area_label.hide()
        else:
            self.file_list.hide()
            self.drop_area_label.show()
            self.preview_area.update_image(None)
            self.label_page_info.setText("0 / 0")

    def _clear_files(self):
        self.file_list.clear()
        self.image_cache.clear() # Clear cache
        self._update_file_count()
        self._update_preview()
        
    def _reset_config(self):
        self.rb_hsr.setChecked(True)
        self.combo_size.setCurrentText("A4")
        self.combo_orient.setCurrentText("纵向")
        self.spin_width.setValue(210)
        self.spin_height.setValue(297)
        self.margin_top.setValue(12)
        self.margin_right.setValue(12)
        self.margin_bottom.setValue(12)
        self.margin_left.setValue(12)
        self.switch_merge.setChecked(True)
        self.switch_cut.setChecked(True)
        self.check_binding_hole.setChecked(False)
        self.check_binding_line.setChecked(False)
        self._reset_page_and_update()

    def _save_config(self):
        """保存配置到文件"""
        config = {
            "layout": {
                "2_per_page": self.rb_2_per_page.isChecked(),
                "3_per_page": self.rb_3_per_page.isChecked(),
                "4_per_page": self.rb_4_per_page.isChecked(),
                "6_per_page": self.rb_6_per_page.isChecked(),
                "hsr": self.rb_hsr.isChecked()
            },
            "paper": {
                "size_idx": self.combo_size.currentIndex(),
                "orient_idx": self.combo_orient.currentIndex(),
                "width": self.spin_width.value(),
                "height": self.spin_height.value(),
                "margin_top": self.margin_top.value(),
                "margin_right": self.margin_right.value(),
                "margin_bottom": self.margin_bottom.value(),
                "margin_left": self.margin_left.value()
            },
            "options": {
                "merge": self.switch_merge.isChecked(),
                "cut": self.switch_cut.isChecked(),
                "binding_hole": self.check_binding_hole.isChecked(),
                "hole_pos_idx": self.combo_hole_pos.currentIndex(),
                "hole_count_idx": self.combo_hole_count.currentIndex(),
                "binding_line": self.check_binding_line.isChecked(),
                "line_pos_idx": self.combo_line_pos.currentIndex(),
                "line_style_idx": self.combo_line_style.currentIndex()
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            QMessageBox.information(self, "成功", "配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {e}")

    def _load_config(self):
        """加载配置"""
        if not os.path.exists(CONFIG_FILE):
            return
            
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Layout
            if "layout" in config:
                l = config["layout"]
                if l.get("2_per_page"): self.rb_2_per_page.setChecked(True)
                elif l.get("3_per_page"): self.rb_3_per_page.setChecked(True)
                elif l.get("4_per_page"): self.rb_4_per_page.setChecked(True)
                elif l.get("6_per_page"): self.rb_6_per_page.setChecked(True)
                elif l.get("hsr"): self.rb_hsr.setChecked(True)
                
            # Paper
            if "paper" in config:
                p = config["paper"]
                self.combo_size.setCurrentIndex(p.get("size_idx", 0))
                self.combo_orient.setCurrentIndex(p.get("orient_idx", 0))
                self.spin_width.setValue(p.get("width", 210))
                self.spin_height.setValue(p.get("height", 297))
                self.margin_top.setValue(p.get("margin_top", 12))
                self.margin_right.setValue(p.get("margin_right", 12))
                self.margin_bottom.setValue(p.get("margin_bottom", 12))
                self.margin_left.setValue(p.get("margin_left", 12))
                
            # Options
            if "options" in config:
                o = config["options"]
                self.switch_merge.setChecked(o.get("merge", True))
                self.switch_cut.setChecked(o.get("cut", True))
                self.check_binding_hole.setChecked(o.get("binding_hole", False))
                self.combo_hole_pos.setCurrentIndex(o.get("hole_pos_idx", 0))
                self.combo_hole_count.setCurrentIndex(o.get("hole_count_idx", 0))
                self.check_binding_line.setChecked(o.get("binding_line", False))
                self.combo_line_pos.setCurrentIndex(o.get("line_pos_idx", 0))
                self.combo_line_style.setCurrentIndex(o.get("line_style_idx", 0))
                
            # Trigger update
            self._update_preview()
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def _get_layout_config(self):
        """获取布局配置"""
        if self.rb_2_per_page.isChecked():
            return 2, 1 # rows, cols
        elif self.rb_3_per_page.isChecked():
            return 3, 1
        elif self.rb_4_per_page.isChecked():
            return 2, 2
        elif self.rb_6_per_page.isChecked():
            return 3, 2
        else: # 高铁票或默认
            return 2, 2 # 默认4张一页

    def _get_file_image(self, file_path):
        """获取文件图像(带缓存)"""
        # Check cache
        if file_path in self.image_cache:
            return self.image_cache[file_path]
            
        img = None
        try:
            if file_path.lower().endswith('.pdf'):
                # Render PDF first page
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(dpi=150)
                    img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888).copy()
                doc.close()
            else:
                img = QImage(file_path)
        except Exception as e:
            logger.error(f"Error loading image {file_path}: {e}")
            return None
            
        if img:
            self.image_cache[file_path] = img
            
        return img

    def _render_page_content(self, painter, rect, files, start_index, end_index, rows, cols):
        """渲染页面内容的通用逻辑"""
        items_per_page = rows * cols
        
        cell_width = rect.width() / cols
        cell_height = rect.height() / rows
        
        for i in range(start_index, end_index):
            page_index = i % items_per_page
            row = page_index // cols
            col = page_index % cols
            
            x = rect.x() + col * cell_width
            y = rect.y() + row * cell_height
            
            file_path = files[i]
            
            # 使用带缓存的加载方法
            img = self._get_file_image(file_path)
                
            if img and not img.isNull():
                # 保持比例缩放以适应单元格，预留 padding
                padding = 10
                target_w = int(cell_width - padding * 2)
                target_h = int(cell_height - padding * 2)
                
                if target_w > 0 and target_h > 0:
                    scaled_img = img.scaled(
                        target_w, target_h,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    
                    # 居中绘制
                    draw_x = x + padding + (target_w - scaled_img.width()) / 2
                    draw_y = y + padding + (target_h - scaled_img.height()) / 2
                    
                    painter.drawImage(int(draw_x), int(draw_y), scaled_img)
            
            # 绘制边框或裁剪线
            if self.switch_cut.isChecked():
                painter.setPen(Qt.DashLine)
                painter.drawRect(int(x), int(y), int(cell_width), int(cell_height))
    
    def _prev_page(self):
        if self.current_preview_page > 0:
            self.current_preview_page = max(0, self.current_preview_page - 2)
            self._update_preview()
            
    def _next_page(self):
        # Allow going to next page if there are more pages to show
        if self.current_preview_page + 2 < self.total_preview_pages:
            self.current_preview_page += 2
            self._update_preview()
            
    def _reset_page_and_update(self):
        """重置页码并更新"""
        self.current_preview_page = 0
        self._update_preview()

    def _update_preview(self):
        """更新实时预览 (双页模式)"""
        if self.file_list.count() == 0:
            self.preview_area.update_image(None)
            self.label_page_info.setText("0 / 0")
            return

        # 1. Calculate Single Page Dimensions (Pixels)
        width_mm = 210
        height_mm = 297
        
        size_text = self.combo_size.currentText()
        if size_text == "A4":
            width_mm, height_mm = 210, 297
        elif size_text == "A5":
            width_mm, height_mm = 148, 210
        elif size_text == "Letter":
            width_mm, height_mm = 216, 279
        else: # Custom
            width_mm = self.spin_width.value()
            height_mm = self.spin_height.value()
            
        if self.combo_orient.currentText() == "横向":
            width_mm, height_mm = height_mm, width_mm
            
        # Preview Scale
        scale_factor = 3.78 * 1.5 # ~144 DPI
        
        page_px_width = int(width_mm * scale_factor)
        page_px_height = int(height_mm * scale_factor)
        
        # 2. Calculate Layout & Pagination
        files = []
        for i in range(self.file_list.count()):
            files.append(self.file_list.item(i).text())
            
        rows, cols = self._get_layout_config()
        if not self.switch_merge.isChecked():
             rows, cols = 1, 1
        items_per_page = rows * cols
        
        self.total_preview_pages = math.ceil(len(files) / items_per_page)
        
        # Ensure current_preview_page is even (0, 2, 4...)
        if self.current_preview_page % 2 != 0:
             self.current_preview_page -= 1
        
        # Clamp
        if self.current_preview_page >= self.total_preview_pages and self.total_preview_pages > 0:
             # Go to last pair
             last_even = (self.total_preview_pages - 1) // 2 * 2
             self.current_preview_page = max(0, last_even)

        # Update controls
        display_end = min(self.current_preview_page + 2, self.total_preview_pages)
        if self.total_preview_pages == 0:
            self.label_page_info.setText("0 / 0")
            self.btn_prev_page.setEnabled(False)
            self.btn_next_page.setEnabled(False)
        else:
            self.label_page_info.setText(f"{self.current_preview_page + 1}-{display_end} / {self.total_preview_pages}")
            self.btn_prev_page.setEnabled(self.current_preview_page > 0)
            self.btn_next_page.setEnabled(self.current_preview_page + 2 < self.total_preview_pages)

        # 3. Create Canvas for 2 Pages
        gap_px = 40 # Gap between pages
        header_px = 60 # Space for "Page X" text
        
        canvas_width = page_px_width * 2 + gap_px * 3 # gap-page-gap-page-gap
        canvas_height = page_px_height + gap_px * 2 + header_px 
        
        canvas_img = QImage(canvas_width, canvas_height, QImage.Format_RGB888)
        canvas_img.fill(QColor("#525659")) # Match background
        
        painter = QPainter(canvas_img)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Font for labels
        font = painter.font()
        font.setPixelSize(24)
        font.setBold(True)
        painter.setFont(font)
        
        # Render Loop
        for offset in range(2):
            p_idx = self.current_preview_page + offset
            if p_idx >= self.total_preview_pages:
                break
                
            # Calculate position
            x_off = gap_px + offset * (page_px_width + gap_px)
            y_off = gap_px + header_px
            
            # Draw "Page X" Label
            label_rect = QRectF(x_off, gap_px, page_px_width, header_px)
            painter.setPen(Qt.white)
            painter.drawText(label_rect, Qt.AlignCenter, f"第 {p_idx + 1} 页")
            
            # Draw Paper Background
            paper_rect = QRectF(x_off, y_off, page_px_width, page_px_height)
            painter.fillRect(paper_rect, Qt.white)
            
            # Render Content
            # Margins
            m_left = self.margin_left.value() * scale_factor
            m_top = self.margin_top.value() * scale_factor
            m_right = self.margin_right.value() * scale_factor
            m_bottom = self.margin_bottom.value() * scale_factor
            
            content_rect = QRectF(
                x_off + m_left, y_off + m_top,
                page_px_width - m_left - m_right,
                page_px_height - m_top - m_bottom
            )
            
            start_idx = p_idx * items_per_page
            end_idx = min((p_idx + 1) * items_per_page, len(files))
            
            self._render_page_content(painter, content_rect, files, start_idx, end_idx, rows, cols)
            
        painter.end()
        self.preview_area.update_image(canvas_img)

    def _handle_export(self):
        """处理合并导出"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出合并PDF", "output.pdf", "PDF Files (*.pdf)")
        if file_path:
            # Use Fast PyMuPDF export
            success, msg = self._fast_export_pdf(file_path)
            if success:
                QMessageBox.information(self, "成功", "导出成功")
                # Open folder?
                # QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(file_path)))
            else:
                QMessageBox.critical(self, "错误", f"导出失败: {msg}")

    def _fast_export_pdf(self, output_path):
        """使用 PyMuPDF 快速合并导出"""
        try:
            files = []
            for i in range(self.file_list.count()):
                files.append(self.file_list.item(i).text())
                
            if not files:
                return False, "没有文件"
            
            # Get Dimensions in Points (1 mm = 2.83465 pt)
            MM_TO_PT = 2.83465
            
            width_mm = 210
            height_mm = 297
            
            size_text = self.combo_size.currentText()
            if size_text == "A4":
                width_mm, height_mm = 210, 297
            elif size_text == "A5":
                width_mm, height_mm = 148, 210
            elif size_text == "Letter":
                width_mm, height_mm = 216, 279
            else: # Custom
                width_mm = self.spin_width.value()
                height_mm = self.spin_height.value()
                
            if self.combo_orient.currentText() == "横向":
                width_mm, height_mm = height_mm, width_mm
                
            page_width = width_mm * MM_TO_PT
            page_height = height_mm * MM_TO_PT
            
            # Layout
            rows, cols = self._get_layout_config()
            if not self.switch_merge.isChecked():
                rows, cols = 1, 1
            
            items_per_page = rows * cols
            total_pages = math.ceil(len(files) / items_per_page)
            
            # Margins
            m_left = self.margin_left.value() * MM_TO_PT
            m_top = self.margin_top.value() * MM_TO_PT
            m_right = self.margin_right.value() * MM_TO_PT
            m_bottom = self.margin_bottom.value() * MM_TO_PT
            
            # Content Area
            content_rect = fitz.Rect(
                m_left, m_top,
                page_width - m_right,
                page_height - m_bottom
            )
            
            cell_width = content_rect.width / cols
            cell_height = content_rect.height / rows
            
            doc = fitz.open()
            
            for p in range(total_pages):
                page = doc.new_page(width=page_width, height=page_height)
                
                start_idx = p * items_per_page
                end_idx = min((p + 1) * items_per_page, len(files))
                
                for i in range(start_idx, end_idx):
                    file_path = files[i]
                    page_index = i % items_per_page
                    row = page_index // cols
                    col = page_index % cols
                    
                    x = content_rect.x0 + col * cell_width
                    y = content_rect.y0 + row * cell_height
                    
                    # Target Rect for content (with padding logic same as preview)
                    padding = 10 * MM_TO_PT / 3.78 # Approximate padding scaling or keep consistent? 
                    # Actually preview used 10 pixels padding. 
                    # Let's use a small padding in points, e.g. 5 pt
                    padding = 5 
                    
                    target_rect = fitz.Rect(
                        x + padding, y + padding,
                        x + cell_width - padding,
                        y + cell_height - padding
                    )
                    
                    try:
                        if file_path.lower().endswith('.pdf'):
                            src_doc = fitz.open(file_path)
                            if len(src_doc) > 0:
                                # show_pdf_page keeps vector data!
                                page.show_pdf_page(target_rect, src_doc, 0)
                            src_doc.close()
                        else:
                            # Insert Image
                            page.insert_image(target_rect, filename=file_path, keep_proportion=True)
                    except Exception as e:
                        logger.error(f"Error inserting {file_path}: {e}")
                        
                    # Draw Cut Lines (if enabled)
                    if self.switch_cut.isChecked():
                        # Draw dashed rect around cell
                        shape = page.new_shape()
                        shape.draw_rect(fitz.Rect(x, y, x + cell_width, y + cell_height))
                        shape.finish(color=(0, 0, 0), dashes=[3]) # Black dashed
                        shape.commit()

            doc.save(output_path)
            doc.close()
            return True, "Success"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)
