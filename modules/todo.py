from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QListWidget, QLineEdit, 
                            QMessageBox, QFrame)
from PyQt5.QtCore import Qt
import json
import os
import sys
from utils.paths import get_app_path

class TodoWindow(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.todo_file = get_app_path('todo_list.json')
        self.init_ui()
        self.load_todos()
        
    def init_ui(self):
        """初始化待办事项界面"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建卡片容器
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        
        # 标题
        title = QLabel("待办事项")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        card_layout.addWidget(title)
        
        # 待办事项列表
        self.todo_list = QListWidget()
        card_layout.addWidget(self.todo_list)
        
        # 添加待办事项区域
        add_layout = QHBoxLayout()
        self.new_todo = QLineEdit()
        self.new_todo.setPlaceholderText("输入新的待办事项...")
        add_layout.addWidget(self.new_todo)
        
        add_btn = QPushButton("添加")
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self.add_todo)
        add_layout.addWidget(add_btn)
        card_layout.addLayout(add_layout)
        
        # 操作按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        delete_btn = QPushButton("删除选中")
        delete_btn.setProperty("class", "warning")
        delete_btn.clicked.connect(self.delete_todo)
        btn_layout.addWidget(delete_btn)
        
        clear_btn = QPushButton("清空所有")
        clear_btn.setProperty("class", "danger")
        clear_btn.clicked.connect(self.clear_todos)
        btn_layout.addWidget(clear_btn)
        
        card_layout.addLayout(btn_layout)
        main_layout.addWidget(card)
        
        self.setLayout(main_layout)
    
    def add_todo(self):
        """添加待办事项"""
        text = self.new_todo.text().strip()
        if text:
            self.todo_list.addItem(text)
            self.new_todo.clear()
            self.save_todos()
        else:
            QMessageBox.warning(self, "警告", "待办事项不能为空!")
    
    def delete_todo(self):
        """删除选中的待办事项"""
        current_item = self.todo_list.currentItem()
        if current_item:
            self.todo_list.takeItem(self.todo_list.row(current_item))
            self.save_todos()
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的待办事项!")
    
    def clear_todos(self):
        """清空所有待办事项"""
        reply = QMessageBox.question(
            self, '确认', 
            '确定要清空所有待办事项吗?',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.todo_list.clear()
            self.save_todos()
    
    def load_todos(self):
        """从文件加载待办事项"""
        if os.path.exists(self.todo_file):
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    todos = json.load(f)
                    for todo in todos:
                        self.todo_list.addItem(todo)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载待办事项失败: {str(e)}")
    
    def save_todos(self):
        """保存待办事项到文件"""
        todos = []
        for i in range(self.todo_list.count()):
            todos.append(self.todo_list.item(i).text())
            
        try:
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                json.dump(todos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存待办事项失败: {str(e)}")