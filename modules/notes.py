from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
import json
import os
import sys
from utils.paths import get_app_path

class NotesWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.notes_file = get_app_path('notes.json')
        self.init_ui()
        self.load_notes()
        
    def init_ui(self):
        """初始化便签界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建卡片容器
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        
        # 标题
        title = QLabel("便签")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #303133;")
        card_layout.addWidget(title)
        
        # 便签编辑区
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("在这里输入您的便签内容...")
        card_layout.addWidget(self.notes_edit)
        
        # 操作按钮区域
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.save_notes)
        btn_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self.clear_notes)
        btn_layout.addWidget(clear_btn)
        
        card_layout.addLayout(btn_layout)
        
        main_layout.addWidget(card)
        self.setLayout(main_layout)
    
    def load_notes(self):
        """从文件加载便签内容"""
        if os.path.exists(self.notes_file):
            try:
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
                    self.notes_edit.setPlainText(notes.get('content', ''))
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载便签失败: {str(e)}")
    
    def save_notes(self):
        """保存便签到文件"""
        content = self.notes_edit.toPlainText()
        try:
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump({'content': content}, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", "便签已保存!")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存便签失败: {str(e)}")
    
    def clear_notes(self):
        """清空便签内容"""
        reply = QMessageBox.question(
            self, '确认', 
            '确定要清空便签内容吗?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.notes_edit.clear()