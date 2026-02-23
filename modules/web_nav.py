import json
import os
import hashlib
import urllib.request
import urllib.parse
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QMessageBox, QGridLayout, QScrollArea, QFrame,
    QMenu, QAction, QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QUrl, QSize, pyqtSignal, QThread
from PyQt5.QtGui import QDesktopServices, QIcon, QPixmap
from utils.paths import get_app_path
from core.logger import logger

DATA_FILE = "web_nav.json"
ICON_DIR = "assets/favicons"

class AddSiteDialog(QDialog):
    def __init__(self, parent=None, name="", url=""):
        super().__init__(parent)
        self.setWindowTitle("添加网站" if not name else "编辑网站")
        self.setFixedSize(400, 200)
        self.initial_name = name
        self.initial_url = url
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：百度")
        self.name_input.setText(self.initial_name)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("例如：https://www.baidu.com")
        self.url_input.setText(self.initial_url)
        
        form_layout.addRow("网站名称:", self.name_input)
        form_layout.addRow("网站地址:", self.url_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_data(self):
        return self.name_input.text().strip(), self.url_input.text().strip()

class FaviconFetcher(QThread):
    finished = pyqtSignal(str, str) # url, icon_filename

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.icon_dir = get_app_path(ICON_DIR)
        if not os.path.exists(self.icon_dir):
            os.makedirs(self.icon_dir, exist_ok=True)

    def run(self):
        try:
            # Basic normalization
            if not self.url.startswith('http'):
                target_url = 'https://' + self.url
            else:
                target_url = self.url
                
            parsed = urllib.parse.urlparse(target_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            favicon_url = f"{base_url}/favicon.ico"
            
            # Hash URL for unique filename
            h = hashlib.md5(target_url.encode('utf-8')).hexdigest()
            filename = f"{h}.ico"
            save_path = os.path.join(self.icon_dir, filename)
            
            # Check if already exists to avoid re-downloading (optional, but good for cache)
            # But user might want to refresh, so we'll overwrite or check logic later.
            # For now, always fetch to ensure we get it.
            
            req = urllib.request.Request(
                favicon_url, 
                data=None, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = response.read()
                if data:
                    with open(save_path, 'wb') as f:
                        f.write(data)
                    self.finished.emit(self.url, filename)
        except Exception as e:
            logger.error(f"Failed to fetch favicon for {self.url}: {e}")
            # Try getting google favicon service as fallback?
            # https://www.google.com/s2/favicons?domain=domain.com
            try:
                self._fetch_google_favicon(target_url, save_path)
            except:
                pass

    def _fetch_google_favicon(self, url, save_path):
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        google_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=32"
        
        req = urllib.request.Request(
            google_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read()
            if data:
                with open(save_path, 'wb') as f:
                    f.write(data)
                filename = os.path.basename(save_path)
                self.finished.emit(self.url, filename)

class WebNavWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.sites = []
        self.last_cols = 0
        self._load_data()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("网站导航")
        title.setProperty("class", "page-title")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        btn_add = QPushButton("添加网站")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._add_site_dialog)
        header_layout.addWidget(btn_add)
        
        layout.addLayout(header_layout)
        
        # Scroll Area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.cards_layout.setSpacing(20)
        scroll.setWidget(self.cards_container)
        
        layout.addWidget(scroll)
        
        # Initial render will happen in resizeEvent or showEvent to know width
        # But we can do initial one with default width
        
    def showEvent(self, event):
        super().showEvent(event)
        self._render_cards()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Check if columns change to avoid flickering
        container_width = self.width() - 60
        card_width = 180 + 20 
        cols = max(1, container_width // card_width)
        if cols != self.last_cols:
            self._render_cards()

    def _load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.sites = json.load(f)
            except:
                self.sites = []

    def _save_data(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def _add_site_dialog(self):
        dialog = AddSiteDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, url = dialog.get_data()
            if name and url:
                if not url.startswith('http'):
                    url = 'https://' + url
                    
                site_data = {"name": name, "url": url}
                self.sites.append(site_data)
                self._save_data()
                self._render_cards()
                
                # Fetch favicon
                self._fetch_favicon(url)

    def _fetch_favicon(self, url):
        worker = FaviconFetcher(url)
        worker.finished.connect(self._on_favicon_fetched)
        # Keep reference to avoid gc
        setattr(self, f"worker_{hash(url)}", worker)
        worker.start()
        
    def _on_favicon_fetched(self, url, filename):
        # Update site data
        changed = False
        for site in self.sites:
            if site["url"] == url:
                site["icon"] = filename
                changed = True
        
        if changed:
            self._save_data()
            self._render_cards()
            
        # Cleanup worker
        worker_name = f"worker_{hash(url)}"
        if hasattr(self, worker_name):
            delattr(self, worker_name)

    def _render_cards(self):
        # Clear existing
        for i in reversed(range(self.cards_layout.count())):
            widget = self.cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            
        # Add cards
        container_width = self.width() - 60 # Subtract margins and scrollbar roughly
        card_width = 180 + 20 # Card width + spacing
        cols_per_row = max(1, container_width // card_width)
        self.last_cols = cols_per_row
        
        row, col = 0, 0
        
        for idx, site in enumerate(self.sites):
            card = self._create_card(idx, site)
            self.cards_layout.addWidget(card, row, col)
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1

    def _create_card(self, idx, site):
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setFixedSize(180, 120)
        
        vbox = QVBoxLayout(frame)
        vbox.setAlignment(Qt.AlignCenter)
        
        # Icon
        lbl_icon = QLabel() 
        lbl_icon.setAlignment(Qt.AlignCenter)
        
        # Check if custom icon exists
        icon_path = None
        if "icon" in site:
            full_path = get_app_path(os.path.join(ICON_DIR, site["icon"]))
            if os.path.exists(full_path):
                icon_path = full_path
                
        if icon_path:
            pixmap = QPixmap(icon_path)
            # Scale if too large
            if pixmap.width() > 48:
                pixmap = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl_icon.setPixmap(pixmap)
        else:
            lbl_icon.setText("🌐")
            lbl_icon.setStyleSheet("font-size: 32px; background: transparent;")
        
        # Name
        lbl_name = QLabel(site["name"])
        lbl_name.setAlignment(Qt.AlignCenter)
        lbl_name.setWordWrap(True)
        lbl_name.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent; margin-top: 5px;")
        
        vbox.addWidget(lbl_icon)
        vbox.addWidget(lbl_name)
        
        # Click event
        frame.mouseReleaseEvent = lambda e, u=site["url"]: self._open_url(u) if e.button() == Qt.LeftButton else None
        
        # Context menu for delete
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        frame.customContextMenuRequested.connect(lambda pos, i=idx: self._show_context_menu(pos, i))
        
        frame.setProperty("class", "web-card")
        
        return frame

    def _open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def _show_context_menu(self, pos, idx):
        menu = QMenu(self)
        edit_action = menu.addAction("编辑")
        delete_action = menu.addAction("删除")
        
        action = menu.exec_(self.sender().mapToGlobal(pos))
        
        if action == delete_action:
            confirm = QMessageBox.question(
                self, "确认删除", 
                "确定要删除这个网站吗？", 
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self._delete_site(idx)
        elif action == edit_action:
            self._edit_site(idx)

    def _edit_site(self, idx):
        if 0 <= idx < len(self.sites):
            site = self.sites[idx]
            old_url = site["url"]
            
            dialog = AddSiteDialog(self, name=site["name"], url=old_url)
            if dialog.exec_() == QDialog.Accepted:
                new_name, new_url = dialog.get_data()
                if new_name and new_url:
                    if not new_url.startswith('http'):
                        new_url = 'https://' + new_url
                    
                    site["name"] = new_name
                    site["url"] = new_url
                    
                    self._save_data()
                    self._render_cards()
                    
                    # If URL changed, fetch new favicon
                    if old_url != new_url:
                        # Remove old icon reference maybe? 
                        # Or just overwrite when fetched.
                        # For now just fetch new one.
                        self._fetch_favicon(new_url)

    def _delete_site(self, idx):
        if 0 <= idx < len(self.sites):
            del self.sites[idx]
            self._save_data()
            self._render_cards()
