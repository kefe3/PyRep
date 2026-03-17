"""
file_explorer.py — Sol panel dosya gezgini
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeView, QLabel,
    QPushButton, QHBoxLayout, QFileDialog,
    QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtGui import QFileSystemModel, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QDir


class FileExplorer(QWidget):
    file_opened = pyqtSignal(str)   # dosya yolu gönderir

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(180)
        self.setMaximumWidth(320)
        self.root_path = os.path.expanduser("~")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Başlık
        header = QWidget()
        header.setStyleSheet("background:#252526; border-bottom:1px solid #333333;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 6, 6, 6)

        title = QLabel("EXPLORER")
        title.setStyleSheet(
            "color:#bbbbbb; font-family:Consolas; font-size:9px; "
            "letter-spacing:2px; font-weight:bold;"
        )
        h_layout.addWidget(title)
        h_layout.addStretch()

        open_btn = QPushButton("📂")
        open_btn.setToolTip("Klasör Aç")
        open_btn.setFixedSize(24, 24)
        open_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #4a5568; font-size: 13px;
            }
            QPushButton:hover { color: #00e5ff; }
        """)
        open_btn.clicked.connect(self._open_folder)
        h_layout.addWidget(open_btn)

        layout.addWidget(header)

        # Klasör yolu etiketi
        self.path_label = QLabel("  ~")
        self.path_label.setStyleSheet(
            "color:#969696; font-family:Consolas; font-size:9px; "
            "padding:4px 10px; background:#252526;"
        )
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        # Dosya ağacı
        self.model = QFileSystemModel()
        self.model.setRootPath(self.root_path)
        self.model.setNameFilters(["*.py", "*.txt", "*.md", "*.json", "*.yaml", "*.toml", "*.cfg"])
        self.model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.root_path))
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderHidden(True)

        # Sadece ilk sütun (isim) göster
        for col in range(1, self.model.columnCount()):
            self.tree.hideColumn(col)

        self.tree.setStyleSheet("""
            QTreeView {
                background: #252526;
                color: #cccccc;
                border: none;
                font-family: Consolas;
                font-size: 12px;
            }
            QTreeView::item { padding: 4px 6px; }
            QTreeView::item:hover { background: #2a2d2e; color: #ffffff; }
            QTreeView::item:selected {
                background: #094771;
                color: #ffffff;
            }
            QTreeView::branch { background: #252526; }
        """)

        self.tree.doubleClicked.connect(self._on_double_click)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)

        layout.addWidget(self.tree)

        # Alt butonlar
        bottom = QWidget()
        bottom.setStyleSheet("background:#252526; border-top:1px solid #333333;")
        b_layout = QHBoxLayout(bottom)
        b_layout.setContentsMargins(8, 4, 8, 4)
        b_layout.setSpacing(4)

        new_file_btn = QPushButton("+ Dosya")
        new_file_btn.setStyleSheet(self._btn_style())
        new_file_btn.clicked.connect(self._new_file)

        new_folder_btn = QPushButton("+ Klasör")
        new_folder_btn.setStyleSheet(self._btn_style())
        new_folder_btn.clicked.connect(self._new_folder)

        b_layout.addWidget(new_file_btn)
        b_layout.addWidget(new_folder_btn)
        layout.addWidget(bottom)

    # ── Klasör aç ───────────────────────────
    def _open_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Klasör Seç", self.root_path)
        if path:
            self.root_path = path
            self.model.setRootPath(path)
            self.tree.setRootIndex(self.model.index(path))
            short = ".../" + os.path.basename(path) if len(path) > 30 else path
            self.path_label.setText(f"  {short}")

    # ── Çift tıklama → dosya aç ─────────────
    def _on_double_click(self, index):
        path = self.model.filePath(index)
        if os.path.isfile(path):
            self.file_opened.emit(path)

    # ── Sağ tık menüsü ───────────────────────
    def _context_menu(self, pos):
        index = self.tree.indexAt(pos)
        menu  = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1a1e28; color: #e2e8f0;
                border: 1px solid #252a38;
                font-family: Consolas; font-size: 11px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #252a38; }
        """)

        if index.isValid():
            path = self.model.filePath(index)
            open_act  = QAction("📄 Aç", self)
            open_act.triggered.connect(lambda: self.file_opened.emit(path) if os.path.isfile(path) else None)
            delete_act = QAction("🗑 Sil", self)
            delete_act.triggered.connect(lambda: self._delete_item(path))
            rename_act = QAction("✏ Yeniden Adlandır", self)
            rename_act.triggered.connect(lambda: self._rename_item(path))
            menu.addAction(open_act)
            menu.addSeparator()
            menu.addAction(rename_act)
            menu.addAction(delete_act)
        else:
            new_act = QAction("+ Yeni Dosya", self)
            new_act.triggered.connect(self._new_file)
            menu.addAction(new_act)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ── Yeni dosya / klasör ──────────────────
    def _new_file(self):
        name, ok = QInputDialog.getText(self, "Yeni Dosya", "Dosya adı:")
        if ok and name:
            path = os.path.join(self.root_path, name)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "Yeni Klasör", "Klasör adı:")
        if ok and name:
            try:
                os.makedirs(os.path.join(self.root_path, name), exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    # ── Sil / yeniden adlandır ───────────────
    def _delete_item(self, path):
        reply = QMessageBox.question(
            self, "Sil", f"{os.path.basename(path)} silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    import shutil
                    shutil.rmtree(path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    def _rename_item(self, path):
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Yeniden Adlandır", "Yeni ad:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            try:
                os.rename(path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    # ── Stil ────────────────────────────────
    def _btn_style(self):
        return """
            QPushButton {
                background: transparent;
                border: 1px solid #252a38;
                border-radius: 4px;
                color: #4a5568;
                font-family: Consolas;
                font-size: 10px;
                padding: 3px 8px;
            }
            QPushButton:hover { color: #e2e8f0; border-color: #4a5568; }
        """