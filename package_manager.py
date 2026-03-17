"""
package_manager.py — Görsel kütüphane yöneticisi
Kur / Sil / Listele — arka planda pip çalışır, arayüz donmaz
"""

import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QTextEdit, QWidget, QTabWidget, QMessageBox, QProgressBar
)
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal


# ─────────────────────────────────────────────
#  pip komutunu arka planda çalıştıran thread
# ─────────────────────────────────────────────
class PipThread(QThread):
    output   = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(bool)   # True = başarılı

    def __init__(self, args: list):
        """
        args örnek:
          ["install", "numpy"]
          ["uninstall", "-y", "numpy"]
          ["list"]
        """
        super().__init__()
        self.args = args

    def run(self):
        try:
            import sys
            cmd = [sys.executable, "-m", "pip"] + self.args

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                self.output.emit(line.rstrip())
            for line in proc.stderr:
                self.error.emit(line.rstrip())

            proc.wait()
            self.finished.emit(proc.returncode == 0)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False)


# ─────────────────────────────────────────────
#  Ana diyalog
# ─────────────────────────────────────────────
class PackageManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📦 Kütüphane Yöneticisi — PyRep")
        self.resize(700, 520)
        self.setStyleSheet("""
            QDialog {
                background: #0d0f14;
                color: #e2e8f0;
                font-family: Consolas;
            }
        """)
        self.pip_thread = None
        self._build_ui()
        self._load_installed()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Başlık
        header = QLabel("  📦  Kütüphane Yöneticisi")
        header.setStyleSheet("""
            background: #13161d;
            color: #00e5ff;
            font-size: 14px;
            font-weight: bold;
            padding: 12px 16px;
            border-bottom: 1px solid #252a38;
            letter-spacing: 1px;
        """)
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane   { border: none; background: #0d0f14; }
            QTabBar::tab       { background: #13161d; color: #4a5568;
                                 padding: 8px 20px; border: none;
                                 font-family: Consolas; font-size: 11px; }
            QTabBar::tab:selected { background: #0d0f14; color: #e2e8f0;
                                    border-bottom: 2px solid #00e5ff; }
            QTabBar::tab:hover { color: #e2e8f0; }
        """)
        layout.addWidget(tabs)

        # ── Sekme 1: Kur ────────────────────
        install_tab = QWidget()
        i_layout    = QVBoxLayout(install_tab)
        i_layout.setContentsMargins(16, 16, 16, 16)
        i_layout.setSpacing(10)

        i_label = QLabel("Paket adı yaz ve 'Kur' butonuna bas:")
        i_label.setStyleSheet("color:#4a5568; font-size:11px;")
        i_layout.addWidget(i_label)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        self.install_input = QLineEdit()
        self.install_input.setPlaceholderText("örn: numpy  /  pandas==2.1.0  /  flask requests")
        self.install_input.setStyleSheet(self._input_style())
        self.install_input.returnPressed.connect(self._install)
        row_layout.addWidget(self.install_input)

        install_btn = QPushButton("▶  Kur")
        install_btn.setStyleSheet(self._btn_style("#00ff88", "#0d3320"))
        install_btn.setFixedWidth(90)
        install_btn.clicked.connect(self._install)
        row_layout.addWidget(install_btn)

        i_layout.addWidget(row)

        # Popüler kütüphaneler
        pop_label = QLabel("Popüler kütüphaneler:")
        pop_label.setStyleSheet("color:#4a5568; font-size:10px; margin-top:6px;")
        i_layout.addWidget(pop_label)

        pop_row = QWidget()
        pop_layout = QHBoxLayout(pop_row)
        pop_layout.setContentsMargins(0, 0, 0, 0)
        pop_layout.setSpacing(6)

        popular = ["numpy", "pandas", "matplotlib", "requests", "flask", "fastapi", "pillow", "scikit-learn"]
        for pkg in popular:
            btn = QPushButton(pkg)
            btn.setStyleSheet(self._tag_btn_style())
            btn.clicked.connect(lambda checked, p=pkg: self._quick_install(p))
            pop_layout.addWidget(btn)
        pop_layout.addStretch()

        i_layout.addWidget(pop_row)
        i_layout.addStretch()
        tabs.addTab(install_tab, "➕ Kur")

        # ── Sekme 2: Kurulu kütüphaneler ────
        installed_tab = QWidget()
        inst_layout   = QVBoxLayout(installed_tab)
        inst_layout.setContentsMargins(16, 16, 16, 16)
        inst_layout.setSpacing(8)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kütüphane ara...")
        self.search_input.setStyleSheet(self._input_style())
        self.search_input.textChanged.connect(self._filter_list)
        top_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setStyleSheet(self._btn_style("#4a5568", "#1a1e28"))
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._load_installed)
        top_layout.addWidget(refresh_btn)

        inst_layout.addWidget(top_row)

        self.pkg_list = QListWidget()
        self.pkg_list.setStyleSheet("""
            QListWidget {
                background: #13161d;
                border: 1px solid #252a38;
                border-radius: 6px;
                color: #e2e8f0;
                font-family: Consolas;
                font-size: 12px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
            }
            QListWidget::item:hover    { background: #1a1e28; }
            QListWidget::item:selected { background: rgba(255,68,102,0.12);
                                          color: #ff4466; }
        """)
        inst_layout.addWidget(self.pkg_list)

        uninstall_btn = QPushButton("🗑  Seçili kütüphaneyi sil")
        uninstall_btn.setStyleSheet(self._btn_style("#ff4466", "#2a0d14"))
        uninstall_btn.clicked.connect(self._uninstall)
        inst_layout.addWidget(uninstall_btn)

        tabs.addTab(installed_tab, "📋 Kurulu")

        # ── Alt log paneli ───────────────────
        log_header = QLabel("  ◆  PIP ÇIKTISI")
        log_header.setStyleSheet("""
            background: #13161d;
            color: #4a5568;
            font-size: 9px;
            letter-spacing: 2px;
            padding: 5px 12px;
            border-top: 1px solid #252a38;
        """)
        layout.addWidget(log_header)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(__import__("PyQt6.QtGui", fromlist=["QFont"]).QFont("Consolas", 10))
        self.log.setFixedHeight(130)
        self.log.setStyleSheet("""
            QTextEdit {
                background: #0a0c10;
                color: #00ff88;
                border: none;
                padding: 8px 12px;
            }
        """)
        layout.addWidget(self.log)

        # İlerleme çubuğu
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)   # belirsiz mod
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.hide()
        self.progress.setStyleSheet("""
            QProgressBar { background: #13161d; border: none; }
            QProgressBar::chunk { background: #00e5ff; }
        """)
        layout.addWidget(self.progress)

    # ── Kur ─────────────────────────────────
    def _install(self):
        text = self.install_input.text().strip()
        if not text:
            return
        packages = text.split()
        self._run_pip(["install"] + packages, f"Kuruluyor: {', '.join(packages)}")
        self.install_input.clear()

    def _quick_install(self, pkg):
        self._run_pip(["install", pkg], f"Kuruluyor: {pkg}")

    # ── Sil ─────────────────────────────────
    def _uninstall(self):
        item = self.pkg_list.currentItem()
        if not item:
            QMessageBox.information(self, "Uyarı", "Lütfen bir kütüphane seçin.")
            return
        pkg_name = item.text().split()[0]
        reply = QMessageBox.question(
            self, "Sil",
            f"'{pkg_name}' kütüphanesi silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_pip(["uninstall", "-y", pkg_name], f"Siliniyor: {pkg_name}")

    # ── Kurulu listele ───────────────────────
    def _load_installed(self):
        self.pkg_list.clear()
        self._print_log("Kurulu kütüphaneler listeleniyor...", "#00e5ff")

        self.list_thread = PipThread(["list"])
        self.list_thread.output.connect(self._add_to_list)
        self.list_thread.error.connect(lambda s: self._print_log(s, "#ff4466"))
        self.list_thread.finished.connect(lambda ok: self._print_log(
            f"✅ {self.pkg_list.count()} kütüphane bulundu." if ok else "❌ Liste alınamadı.",
            "#00ff88" if ok else "#ff4466"
        ))
        self.list_thread.start()

    def _add_to_list(self, line: str):
        # pip list çıktısı: "Package    Version"
        if line.startswith("Package") or line.startswith("---"):
            return
        self.pkg_list.addItem(line)

    def _filter_list(self, text: str):
        for i in range(self.pkg_list.count()):
            item = self.pkg_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ── pip çalıştır ────────────────────────
    def _run_pip(self, args: list, label: str = ""):
        if self.pip_thread and self.pip_thread.isRunning():
            self._print_log("⚠ Başka bir işlem devam ediyor, lütfen bekleyin.", "#ffd700")
            return

        self.progress.show()
        if label:
            self._print_log(f"▶ {label}", "#00e5ff")

        self.pip_thread = PipThread(args)
        self.pip_thread.output.connect(lambda s: self._print_log(s, "#00ff88"))
        self.pip_thread.error.connect(lambda s: self._print_log(s, "#ffd700"))
        self.pip_thread.finished.connect(self._on_pip_done)
        self.pip_thread.start()

    def _on_pip_done(self, success: bool):
        self.progress.hide()
        if success:
            self._print_log("✅ İşlem tamamlandı.\n", "#00ff88")
        else:
            self._print_log("❌ İşlem başarısız.\n", "#ff4466")
        # Kurulu listesini yenile
        self._load_installed()

    def _print_log(self, text: str, color: str = "#00ff88"):
        cursor = self.log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(text + "\n", fmt)
        self.log.setTextCursor(cursor)
        self.log.ensureCursorVisible()

    # ── Stiller ─────────────────────────────
    def _input_style(self):
        return """
            QLineEdit {
                background: #13161d;
                border: 1px solid #252a38;
                border-radius: 6px;
                color: #e2e8f0;
                font-family: Consolas;
                font-size: 12px;
                padding: 7px 12px;
            }
            QLineEdit:focus { border-color: #00e5ff; }
        """

    def _btn_style(self, color, bg):
        return f"""
            QPushButton {{
                background: {bg};
                border: 1px solid {color}44;
                border-radius: 6px;
                color: {color};
                font-family: Consolas;
                font-size: 11px;
                font-weight: bold;
                padding: 7px 12px;
            }}
            QPushButton:hover {{
                background: {color}22;
                border-color: {color};
            }}
            QPushButton:disabled {{ opacity: 0.4; }}
        """

    def _tag_btn_style(self):
        return """
            QPushButton {
                background: rgba(124,58,237,0.1);
                border: 1px solid rgba(124,58,237,0.3);
                border-radius: 12px;
                color: #a78bfa;
                font-family: Consolas;
                font-size: 10px;
                padding: 3px 10px;
            }
            QPushButton:hover {
                background: rgba(124,58,237,0.25);
                border-color: #7c3aed;
                color: #c4b5fd;
            }
        """
