"""
editor.py — Ana pencere
Özellikler:
  - Kod editörü + syntax renklendirme
  - Terminal (çıktı + komut yazma)
  - Ctrl+F ile kod içi arama
  - Dosya ve kütüphane arama
  - Python öğrenme modu (konu + alıştırma)
"""

import os
import subprocess
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTextEdit, QPlainTextEdit, QPushButton,
    QLabel, QTabWidget, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QFrame, QLineEdit,
    QDialog, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter,
    QTextCursor, QKeySequence, QAction
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRegularExpression

from file_explorer import FileExplorer
from package_manager import PackageManagerDialog


# ─────────────────────────────────────────────
#  Python Syntax Highlighter (VS Code Dark+)
# ─────────────────────────────────────────────
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        def fmt(color, bold=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(700)
            return f

        keywords = [
            "False","None","True","and","as","assert","async","await",
            "break","class","continue","def","del","elif","else","except",
            "finally","for","from","global","if","import","in","is",
            "lambda","nonlocal","not","or","pass","raise","return",
            "try","while","with","yield"
        ]
        for kw in keywords:
            self.rules.append((QRegularExpression(rf"\b{kw}\b"), fmt("#569cd6", bold=True)))

        builtins = ["print","len","range","input","int","str","float","list",
                    "dict","set","tuple","type","open","sum","min","max",
                    "abs","round","enumerate","zip","map","filter","sorted"]
        for b in builtins:
            self.rules.append((QRegularExpression(rf"\b{b}\b"), fmt("#dcdcaa")))

        self.rules += [
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), fmt("#ce9178")),
            (QRegularExpression(r"'[^'\\]*(\\.[^'\\]*)*'"), fmt("#ce9178")),
            (QRegularExpression(r'f"[^"]*"'),               fmt("#ce9178")),
            (QRegularExpression(r"f'[^']*'"),               fmt("#ce9178")),
            (QRegularExpression(r"\b\d+(\.\d+)?\b"),        fmt("#b5cea8")),
            (QRegularExpression(r"#[^\n]*"),                fmt("#6a9955")),
            (QRegularExpression(r"@\w+"),                   fmt("#c586c0")),
            (QRegularExpression(r"\bclass\s+\w+"),          fmt("#4ec9b0", bold=True)),
            (QRegularExpression(r"\bdef\s+\w+"),            fmt("#dcdcaa", bold=True)),
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# ─────────────────────────────────────────────
#  Kod çalıştırma thread'i
# ─────────────────────────────────────────────
class RunThread(QThread):
    output   = pyqtSignal(str)
    error    = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, code: str):
        super().__init__()
        self.code = code

    def run(self):
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(self.code)
                tmp = f.name
            proc = subprocess.Popen(
                [sys.executable, tmp],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace"
            )
            for line in proc.stdout:
                self.output.emit(line.rstrip())
            for line in proc.stderr:
                self.error.emit(line.rstrip())
            proc.wait()
            os.unlink(tmp)
            self.finished.emit(proc.returncode)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(1)


# ─────────────────────────────────────────────
#  Satır numarası alanı
# ─────────────────────────────────────────────
class LineNumberArea(QFrame):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.setFixedWidth(48)
        self.setStyleSheet("background:#1e1e1e; border-right:1px solid #333;")

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))
        painter.setFont(QFont("Consolas", 10))
        painter.setPen(QColor("#858585"))
        block     = self.editor.firstVisibleBlock()
        block_num = block.blockNumber()
        top       = int(self.editor.blockBoundingGeometry(block)
                        .translated(self.editor.contentOffset()).top())
        bottom    = top + int(self.editor.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(0, top, self.width()-6,
                    self.editor.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_num+1))
            block = block.next()
            top   = bottom
            bottom = top + int(self.editor.blockBoundingRect(block).height())
            block_num += 1


# ─────────────────────────────────────────────
#  Kod editörü
# ─────────────────────────────────────────────
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 12))
        self.setStyleSheet("""
            QPlainTextEdit {
                background:#1e1e1e; color:#d4d4d4; border:none;
                padding:8px 8px 8px 56px;
                selection-background-color:#264f78;
            }
        """)
        self.setTabStopDistance(32)
        self.line_area = LineNumberArea(self)
        self.blockCountChanged.connect(lambda: self.setViewportMargins(52,0,0,0))
        self.updateRequest.connect(self._update_line_area)
        self.setViewportMargins(52,0,0,0)
        self.highlighter = PythonHighlighter(self.document())

    def _update_line_area(self, rect, dy):
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.line_area.setGeometry(cr.left(), cr.top(), 52, cr.height())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Tab:
            self.insertPlainText("    ")
            return
        if e.key() == Qt.Key.Key_Return:
            cursor = self.textCursor()
            line   = cursor.block().text()
            indent = len(line) - len(line.lstrip())
            if line.rstrip().endswith(":"):
                indent += 4
            super().keyPressEvent(e)
            self.insertPlainText(" " * indent)
            return
        super().keyPressEvent(e)


# ─────────────────────────────────────────────
#  Arama çubuğu (Ctrl+F)
# ─────────────────────────────────────────────
class SearchBar(QWidget):
    def __init__(self, editor: CodeEditor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.matches = []
        self.current = -1
        self.setStyleSheet("background:#252526; border-bottom:1px solid #333;")
        self.setFixedHeight(36)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ara... (Enter: sonraki)")
        self.input.setStyleSheet("""
            QLineEdit { background:#1e1e1e; border:1px solid #555; border-radius:3px;
                        color:#d4d4d4; font-family:Consolas; font-size:12px; padding:3px 8px; }
            QLineEdit:focus { border-color:#007acc; }
        """)
        self.input.textChanged.connect(self._search)
        self.input.returnPressed.connect(self._next)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color:#969696; font-family:Consolas; font-size:10px; min-width:70px;")

        for label, slot in [("↑", self._prev), ("↓", self._next), ("✕", self.hide)]:
            btn = QPushButton(label)
            btn.setFixedSize(24, 24)
            btn.setStyleSheet("""
                QPushButton { background:transparent; border:none; color:#969696; font-size:14px; }
                QPushButton:hover { color:#fff; }
            """)
            btn.clicked.connect(slot)
            layout.addWidget(btn) if label != "↑" else None

        layout.addWidget(QLabel("🔍"))
        layout.addWidget(self.input, 1)
        layout.addWidget(self.result_label)

        for label, slot in [("↑", self._prev), ("↓", self._next), ("✕", self.hide)]:
            btn = QPushButton(label)
            btn.setFixedSize(24, 24)
            btn.setStyleSheet("""
                QPushButton { background:transparent; border:none; color:#969696; font-size:14px; }
                QPushButton:hover { color:#fff; }
            """)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

    def show_and_focus(self):
        self.show()
        self.input.setFocus()
        self.input.selectAll()

    def _search(self, text):
        self.matches = []
        self.current = -1
        # Eski vurguları temizle
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        clear_fmt = QTextCharFormat()
        clear_fmt.setBackground(QColor("#1e1e1e"))
        cursor.setCharFormat(clear_fmt)
        cursor.clearSelection()
        self.editor.setTextCursor(cursor)

        if not text:
            self.result_label.setText("")
            return

        doc = self.editor.document()
        hl_fmt = QTextCharFormat()
        hl_fmt.setBackground(QColor("#613a00"))
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(text, cursor)
            if cursor.isNull():
                break
            self.matches.append(QTextCursor(cursor))
            cursor.mergeCharFormat(hl_fmt)

        count = len(self.matches)
        self.result_label.setText(f"{count} sonuç" if count else "Bulunamadı")
        if self.matches:
            self.current = 0
            self._go_to(0)

    def _go_to(self, idx):
        if not self.matches:
            return
        active_fmt = QTextCharFormat()
        active_fmt.setBackground(QColor("#ff8c00"))
        c = self.matches[idx]
        c.mergeCharFormat(active_fmt)
        self.editor.setTextCursor(c)
        self.editor.ensureCursorVisible()
        self.result_label.setText(f"{idx+1}/{len(self.matches)}")

    def _next(self):
        if self.matches:
            self.current = (self.current + 1) % len(self.matches)
            self._go_to(self.current)

    def _prev(self):
        if self.matches:
            self.current = (self.current - 1) % len(self.matches)
            self._go_to(self.current)


# ─────────────────────────────────────────────
#  Genel Arama Diyaloğu
# ─────────────────────────────────────────────
class _PipInstallThread(QThread):
    done = pyqtSignal(bool)
    def __init__(self, pkg):
        super().__init__()
        self.pkg = pkg
    def run(self):
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "install", self.pkg],
                               capture_output=True)
            self.done.emit(r.returncode == 0)
        except Exception:
            self.done.emit(False)


class GlobalSearchDialog(QDialog):
    PACKAGES = [
        "numpy","pandas","matplotlib","requests","flask","django","fastapi",
        "uvicorn","sqlalchemy","pillow","scikit-learn","tensorflow","torch",
        "keras","opencv-python","scipy","seaborn","plotly","pytest","black",
        "flake8","mypy","pydantic","celery","redis","pymongo","psycopg2",
        "aiohttp","httpx","beautifulsoup4","scrapy","selenium","paramiko",
        "cryptography","boto3","tweepy","rich","click","typer","pygame"
    ]

    def __init__(self, root_path, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.setWindowTitle("🔍 Arama")
        self.resize(520, 440)
        self.setStyleSheet("QDialog { background:#1e1e1e; color:#d4d4d4; font-family:Consolas; }")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#1e1e1e; }
            QTabBar::tab { background:#2d2d2d; color:#969696; padding:6px 18px;
                           font-family:Consolas; font-size:11px; border:none; }
            QTabBar::tab:selected { background:#1e1e1e; color:#fff; border-top:1px solid #007acc; }
        """)

        # Dosya sekmesi
        ft = QWidget()
        fl = QVBoxLayout(ft)
        fl.setSpacing(8)
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Dosya adı ara...")
        self.file_input.setStyleSheet(self._input_style())
        self.file_input.textChanged.connect(self._search_files)
        self.file_list = QListWidget()
        self.file_list.setStyleSheet(self._list_style())
        fl.addWidget(self.file_input)
        fl.addWidget(self.file_list)
        tabs.addTab(ft, "📄 Dosya")

        # Kütüphane sekmesi
        pt = QWidget()
        pl = QVBoxLayout(pt)
        pl.setSpacing(8)
        self.pkg_input = QLineEdit()
        self.pkg_input.setPlaceholderText("Kütüphane ara... (örn: numpy, flask)")
        self.pkg_input.setStyleSheet(self._input_style())
        self.pkg_input.textChanged.connect(self._search_packages)
        self.pkg_list = QListWidget()
        self.pkg_list.setStyleSheet(self._list_style())
        self.pkg_status = QLabel("")
        self.pkg_status.setStyleSheet("color:#969696; font-size:10px;")
        install_btn = QPushButton("📦 Seçiliyi Kur")
        install_btn.setStyleSheet("""
            QPushButton { background:rgba(0,122,204,0.15); border:1px solid #007acc;
                          border-radius:4px; color:#007acc; font-family:Consolas;
                          font-size:11px; padding:6px 14px; }
            QPushButton:hover { background:rgba(0,122,204,0.3); }
        """)
        install_btn.clicked.connect(self._install_selected)
        pl.addWidget(self.pkg_input)
        pl.addWidget(self.pkg_list)
        pl.addWidget(self.pkg_status)
        pl.addWidget(install_btn)
        tabs.addTab(pt, "📦 Kütüphane")

        layout.addWidget(tabs)

        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet("""
            QPushButton { background:#2d2d2d; border:1px solid #333; border-radius:4px;
                          color:#969696; font-family:Consolas; font-size:11px; padding:6px; }
            QPushButton:hover { color:#fff; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _search_files(self, text):
        self.file_list.clear()
        if not text or not os.path.isdir(self.root_path):
            return
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if text.lower() in f.lower():
                    full = os.path.join(root, f)
                    rel  = os.path.relpath(full, self.root_path)
                    item = QListWidgetItem(f"📄 {rel}")
                    item.setData(Qt.ItemDataRole.UserRole, full)
                    self.file_list.addItem(item)

    def _search_packages(self, text):
        self.pkg_list.clear()
        if not text:
            return
        for p in self.PACKAGES:
            if text.lower() in p.lower():
                self.pkg_list.addItem(QListWidgetItem(f"📦 {p}"))

    def _install_selected(self):
        item = self.pkg_list.currentItem()
        if not item:
            return
        pkg = item.text().replace("📦 ", "").strip()
        self.pkg_status.setText(f"⏳ Kuruluyor: {pkg}...")
        self._pip = _PipInstallThread(pkg)
        self._pip.done.connect(lambda ok, p=pkg: self.pkg_status.setText(
            f"✅ {p} kuruldu!" if ok else f"❌ {p} kurulamadı."
        ))
        self._pip.start()

    def _input_style(self):
        return """
            QLineEdit { background:#252526; border:1px solid #333; border-radius:4px;
                        color:#d4d4d4; font-family:Consolas; font-size:12px; padding:7px 10px; }
            QLineEdit:focus { border-color:#007acc; }
        """

    def _list_style(self):
        return """
            QListWidget { background:#252526; border:1px solid #333; border-radius:4px;
                          color:#cccccc; font-family:Consolas; font-size:12px; }
            QListWidget::item { padding:5px 10px; }
            QListWidget::item:hover { background:#2a2d2e; }
            QListWidget::item:selected { background:#094771; color:#fff; }
        """


# ─────────────────────────────────────────────
#  Python Öğrenme Modu
# ─────────────────────────────────────────────
LESSONS = [
    {
        "title": "1. Değişkenler",
        "content": (
            "Python'da değişken tanımlamak çok basit, tip belirtmene gerek yok.\n\n"
            "Örnekler:\n"
            "    isim = \"Ahmet\"\n"
            "    yas = 20\n"
            "    pi = 3.14\n"
            "    aktif = True\n\n"
            "Çoklu atama:\n"
            "    x, y, z = 1, 2, 3\n"
        ),
        "exercise": 'isim = "Senin adın"\nyas = 18\nprint(f"Merhaba {isim}, {yas} yaşındasın!")',
        "task": "isim değişkenine kendi adını yaz ve ekrana yazdır.",
        "check": "print"
    },
    {
        "title": "2. Koşullar (if/elif/else)",
        "content": (
            "Koşul ifadeleri karar vermeni sağlar.\n\n"
            "Örnek:\n"
            "    yas = 18\n"
            "    if yas >= 18:\n"
            "        print(\"Yetişkin\")\n"
            "    elif yas >= 13:\n"
            "        print(\"Genç\")\n"
            "    else:\n"
            "        print(\"Çocuk\")\n\n"
            "⚠ Girintiler (4 boşluk) zorunludur!"
        ),
        "exercise": 'sayi = 7\nif sayi > 0:\n    print("Pozitif")\nelif sayi < 0:\n    print("Negatif")\nelse:\n    print("Sıfır")',
        "task": "Bir sayı tanımla. 10'dan büyükse 'Büyük', değilse 'Küçük' yazdır.",
        "check": "if"
    },
    {
        "title": "3. Döngüler (for/while)",
        "content": (
            "Döngüler bir işlemi tekrar etmeni sağlar.\n\n"
            "for döngüsü:\n"
            "    for i in range(5):\n"
            "        print(i)   # 0,1,2,3,4\n\n"
            "Liste üzerinde:\n"
            "    for meyve in [\"elma\",\"armut\"]:\n"
            "        print(meyve)\n\n"
            "while döngüsü:\n"
            "    sayac = 0\n"
            "    while sayac < 3:\n"
            "        sayac += 1\n"
        ),
        "exercise": 'for i in range(1, 6):\n    print(f"{i} x 2 = {i*2}")',
        "task": "1'den 10'a kadar olan sayıları ekrana yazdır.",
        "check": "for"
    },
    {
        "title": "4. Fonksiyonlar",
        "content": (
            "Fonksiyonlar tekrar kullanılabilir kod bloklarıdır.\n\n"
            "Tanımlama:\n"
            "    def topla(a, b):\n"
            "        return a + b\n\n"
            "Çağırma:\n"
            "    sonuc = topla(3, 5)\n"
            "    print(sonuc)  # 8\n\n"
            "Varsayılan parametre:\n"
            "    def selam(isim=\"Dünya\"):\n"
            "        print(f\"Merhaba, {isim}!\")\n"
        ),
        "exercise": 'def kare_al(sayi):\n    return sayi ** 2\n\nprint(kare_al(4))   # 16\nprint(kare_al(7))   # 49',
        "task": "İki sayıyı çarpan bir fonksiyon yaz ve 6 x 7'yi yazdır.",
        "check": "def"
    },
    {
        "title": "5. Listeler",
        "content": (
            "Listeler birden fazla değer tutar.\n\n"
            "Oluşturma:\n"
            "    renkler = [\"kırmızı\", \"mavi\", \"yeşil\"]\n\n"
            "Erişim:\n"
            "    print(renkler[0])   # kırmızı\n"
            "    print(renkler[-1])  # son eleman\n\n"
            "İşlemler:\n"
            "    renkler.append(\"sarı\")  # ekle\n"
            "    renkler.remove(\"mavi\")  # sil\n"
            "    print(len(renkler))      # uzunluk\n"
        ),
        "exercise": 'sayilar = [3, 1, 4, 1, 5, 9]\nprint("Toplam:", sum(sayilar))\nprint("En büyük:", max(sayilar))\nprint("Sıralı:", sorted(sayilar))',
        "task": "5 isimden oluşan bir liste oluştur ve hepsini yazdır.",
        "check": "append"
    },
    {
        "title": "6. Sözlükler (dict)",
        "content": (
            "Sözlükler anahtar-değer çiftleri tutar.\n\n"
            "Oluşturma:\n"
            "    kisi = {\n"
            "        \"isim\": \"Ahmet\",\n"
            "        \"yas\": 25\n"
            "    }\n\n"
            "Erişim:\n"
            "    print(kisi[\"isim\"])    # Ahmet\n\n"
            "Döngü:\n"
            "    for k, v in kisi.items():\n"
            "        print(f\"{k}: {v}\")\n"
        ),
        "exercise": 'araba = {"marka": "Toyota", "model": "Corolla", "yil": 2020}\nfor k, v in araba.items():\n    print(f"{k}: {v}")',
        "task": "Ad, yaş ve şehir tutan bir sözlük oluştur ve yazdır.",
        "check": "{"
    },
]


class LearningMode(QWidget):
    def __init__(self, editor_ref, parent=None):
        super().__init__(parent)
        self.editor_ref = editor_ref
        self.current_lesson = 0
        self._build_ui()
        self._load_lesson(0)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sol ders listesi
        left = QWidget()
        left.setFixedWidth(200)
        left.setStyleSheet("background:#252526; border-right:1px solid #333;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        title_lbl = QLabel("  📚 KONULAR")
        title_lbl.setStyleSheet(
            "color:#bbbbbb; font-family:Consolas; font-size:9px; letter-spacing:2px; "
            "padding:10px; background:#1e1e1e; border-bottom:1px solid #333;"
        )
        ll.addWidget(title_lbl)

        self.lesson_list = QListWidget()
        self.lesson_list.setStyleSheet("""
            QListWidget { background:#252526; border:none; color:#cccccc;
                          font-family:Consolas; font-size:12px; }
            QListWidget::item { padding:8px 12px; }
            QListWidget::item:hover { background:#2a2d2e; }
            QListWidget::item:selected { background:#094771; color:#fff; }
        """)
        for lesson in LESSONS:
            self.lesson_list.addItem(lesson["title"])
        self.lesson_list.currentRowChanged.connect(self._load_lesson)
        ll.addWidget(self.lesson_list)
        layout.addWidget(left)

        # Sağ içerik
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Açıklama
        content_w = QWidget()
        content_w.setStyleSheet("background:#1e1e1e;")
        cl = QVBoxLayout(content_w)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(8)

        self.lesson_title_lbl = QLabel("")
        self.lesson_title_lbl.setStyleSheet(
            "color:#007acc; font-family:Consolas; font-size:15px; font-weight:bold;")
        cl.addWidget(self.lesson_title_lbl)

        self.lesson_content = QTextEdit()
        self.lesson_content.setReadOnly(True)
        self.lesson_content.setStyleSheet("""
            QTextEdit { background:#1e1e1e; color:#d4d4d4; border:none;
                        font-family:Consolas; font-size:12px; }
        """)
        cl.addWidget(self.lesson_content)
        right_splitter.addWidget(content_w)

        # Alıştırma
        ex_w = QWidget()
        ex_w.setStyleSheet("background:#252526;")
        el = QVBoxLayout(ex_w)
        el.setContentsMargins(16, 10, 16, 10)
        el.setSpacing(8)

        ex_top = QWidget()
        etl = QHBoxLayout(ex_top)
        etl.setContentsMargins(0, 0, 0, 0)
        ex_title_lbl = QLabel("✏  ALIŞTIRMA")
        ex_title_lbl.setStyleSheet(
            "color:#dcdcaa; font-family:Consolas; font-size:10px; letter-spacing:2px;")
        etl.addWidget(ex_title_lbl)
        etl.addStretch()

        load_btn = QPushButton("📋 Editöre Yükle")
        load_btn.setStyleSheet("""
            QPushButton { background:rgba(0,122,204,0.15); border:1px solid #007acc;
                          border-radius:4px; color:#007acc; font-family:Consolas;
                          font-size:10px; padding:4px 10px; }
            QPushButton:hover { background:rgba(0,122,204,0.3); }
        """)
        load_btn.clicked.connect(self._load_to_editor)
        etl.addWidget(load_btn)
        el.addWidget(ex_top)

        self.task_label = QLabel("")
        self.task_label.setStyleSheet(
            "color:#ce9178; font-family:Consolas; font-size:11px; padding:2px 0;")
        self.task_label.setWordWrap(True)
        el.addWidget(self.task_label)

        self.exercise_code = QPlainTextEdit()
        self.exercise_code.setReadOnly(True)
        self.exercise_code.setMaximumHeight(110)
        self.exercise_code.setStyleSheet("""
            QPlainTextEdit { background:#1e1e1e; color:#d4d4d4; border:1px solid #333;
                             border-radius:4px; font-family:Consolas; font-size:12px; padding:8px; }
        """)
        el.addWidget(self.exercise_code)

        btn_row = QWidget()
        brl = QHBoxLayout(btn_row)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(8)

        check_btn = QPushButton("✅ Kontrol Et")
        check_btn.setStyleSheet("""
            QPushButton { background:rgba(78,201,176,0.12); border:1px solid #4ec9b0;
                          border-radius:4px; color:#4ec9b0; font-family:Consolas;
                          font-size:11px; padding:5px 14px; }
            QPushButton:hover { background:rgba(78,201,176,0.25); }
        """)
        check_btn.clicked.connect(self._check_exercise)

        self.check_result = QLabel("")
        self.check_result.setStyleSheet("font-family:Consolas; font-size:11px;")
        brl.addWidget(check_btn)
        brl.addWidget(self.check_result)
        brl.addStretch()

        for label, slot in [("◀ Önceki", self._prev_lesson), ("Sonraki ▶", self._next_lesson)]:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton { background:#2d2d2d; border:1px solid #333; border-radius:4px;
                              color:#969696; font-family:Consolas; font-size:11px; padding:5px 12px; }
                QPushButton:hover { color:#fff; border-color:#555; }
            """)
            btn.clicked.connect(slot)
            brl.addWidget(btn)

        el.addWidget(btn_row)
        right_splitter.addWidget(ex_w)
        right_splitter.setSizes([300, 220])

        layout.addWidget(right_splitter)

    def _load_lesson(self, idx):
        if idx < 0 or idx >= len(LESSONS):
            return
        self.current_lesson = idx
        lesson = LESSONS[idx]
        self.lesson_title_lbl.setText(lesson["title"])
        self.lesson_content.setPlainText(lesson["content"])
        self.exercise_code.setPlainText(lesson["exercise"])
        self.task_label.setText(f"📌 Görev: {lesson['task']}")
        self.check_result.setText("")
        self.lesson_list.setCurrentRow(idx)

    def _load_to_editor(self):
        self.editor_ref.setPlainText(LESSONS[self.current_lesson]["exercise"])

    def _check_exercise(self):
        lesson = LESSONS[self.current_lesson]
        code   = self.editor_ref.toPlainText()
        if lesson["check"] in code:
            self.check_result.setText("✅ Harika!")
            self.check_result.setStyleSheet("color:#4ec9b0; font-family:Consolas; font-size:11px;")
        else:
            self.check_result.setText("❌ Tekrar dene!")
            self.check_result.setStyleSheet("color:#f44747; font-family:Consolas; font-size:11px;")

    def _prev_lesson(self):
        if self.current_lesson > 0:
            self._load_lesson(self.current_lesson - 1)

    def _next_lesson(self):
        if self.current_lesson < len(LESSONS) - 1:
            self._load_lesson(self.current_lesson + 1)


# ─────────────────────────────────────────────
#  Ana Pencere
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyRep")
        self.resize(1280, 800)
        self.current_file = None
        self.run_thread   = None
        self._build_ui()
        self._build_toolbar()
        self._build_statusbar()
        self._load_default_code()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Sol: dosya gezgini
        self.file_explorer = FileExplorer()
        self.file_explorer.file_opened.connect(self._open_file_from_explorer)
        splitter.addWidget(self.file_explorer)

        # Orta: ana sekmeler
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#1e1e1e; }
            QTabBar::tab { background:#2d2d2d; color:#969696; padding:7px 18px;
                           font-family:Consolas; font-size:11px; border:none; }
            QTabBar::tab:selected { background:#1e1e1e; color:#fff; border-top:1px solid #007acc; }
            QTabBar::tab:hover { color:#d4d4d4; }
        """)

        # ── Editör sekmesi ──
        editor_widget = QWidget()
        ew_layout = QVBoxLayout(editor_widget)
        ew_layout.setContentsMargins(0, 0, 0, 0)
        ew_layout.setSpacing(0)

        v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Editör + arama çubuğu
        editor_container = QWidget()
        ec_layout = QVBoxLayout(editor_container)
        ec_layout.setContentsMargins(0, 0, 0, 0)
        ec_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border:none; background:#1e1e1e; }
            QTabBar::tab { background:#2d2d2d; color:#969696; padding:6px 16px;
                           border:none; font-family:Consolas; font-size:11px; }
            QTabBar::tab:selected { background:#1e1e1e; color:#fff; border-top:1px solid #007acc; }
            QTabBar::tab:hover { color:#d4d4d4; }
        """)
        self.editor = CodeEditor()
        self.tab_widget.addTab(self.editor, "🐍 main.py")

        self.search_bar = SearchBar(self.editor)
        self.search_bar.hide()

        ec_layout.addWidget(self.tab_widget)
        ec_layout.addWidget(self.search_bar)
        v_splitter.addWidget(editor_container)

        # Terminal
        terminal_widget = QWidget()
        tl = QVBoxLayout(terminal_widget)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(0)

        t_header = QLabel("  ▶  ÇIKTI / TERMINAL")
        t_header.setStyleSheet("""
            background:#252526; color:#969696; font-family:Consolas; font-size:10px;
            padding:5px 12px; letter-spacing:2px;
            border-top:1px solid #333; border-bottom:1px solid #333;
        """)
        tl.addWidget(t_header)

        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFont(QFont("Consolas", 11))
        self.terminal.setStyleSheet("""
            QTextEdit { background:#1e1e1e; color:#cccccc; border:none; padding:10px 14px; }
        """)
        tl.addWidget(self.terminal)

        # Komut satırı
        cmd_row = QWidget()
        cmd_row.setStyleSheet("background:#252526; border-top:1px solid #333;")
        cmd_layout = QHBoxLayout(cmd_row)
        cmd_layout.setContentsMargins(8, 4, 8, 4)
        cmd_layout.setSpacing(6)

        prompt_lbl = QLabel("$")
        prompt_lbl.setStyleSheet(
            "color:#4ec9b0; font-family:Consolas; font-size:13px; font-weight:bold;")
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Komut yaz... (örn: ls, pwd, python --version)")
        self.cmd_input.setStyleSheet("""
            QLineEdit { background:#1e1e1e; border:1px solid #333; border-radius:3px;
                        color:#d4d4d4; font-family:Consolas; font-size:12px; padding:4px 8px; }
            QLineEdit:focus { border-color:#007acc; }
        """)
        self.cmd_input.returnPressed.connect(self._run_command)

        run_cmd_btn = QPushButton("▶")
        run_cmd_btn.setFixedSize(28, 28)
        run_cmd_btn.setStyleSheet("""
            QPushButton { background:#007acc; border:none; border-radius:3px; color:#fff; font-size:12px; }
            QPushButton:hover { background:#005f9e; }
        """)
        run_cmd_btn.clicked.connect(self._run_command)

        clear_btn = QPushButton("🗑")
        clear_btn.setFixedSize(28, 28)
        clear_btn.setStyleSheet("""
            QPushButton { background:transparent; border:1px solid #333; border-radius:3px;
                          color:#969696; font-size:12px; }
            QPushButton:hover { color:#fff; }
        """)
        clear_btn.clicked.connect(self.terminal.clear)

        cmd_layout.addWidget(prompt_lbl)
        cmd_layout.addWidget(self.cmd_input, 1)
        cmd_layout.addWidget(run_cmd_btn)
        cmd_layout.addWidget(clear_btn)
        tl.addWidget(cmd_row)

        v_splitter.addWidget(terminal_widget)
        v_splitter.setSizes([550, 250])

        ew_layout.addWidget(v_splitter)
        self.main_tabs.addTab(editor_widget, "🐍 Editör")

        # ── Öğrenme modu sekmesi ──
        self.learning_mode = LearningMode(self.editor)
        self.main_tabs.addTab(self.learning_mode, "📚 Python Öğren")

        splitter.addWidget(self.main_tabs)
        splitter.setSizes([220, 1060])

    def _build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        tb.setStyleSheet("""
            QToolBar { background:#3c3c3c; border-bottom:1px solid #252526;
                       spacing:4px; padding:4px 8px; }
            QToolButton { background:transparent; border:1px solid transparent;
                          border-radius:4px; color:#cccccc; padding:4px 10px;
                          font-family:Consolas; font-size:11px; }
            QToolButton:hover { color:#fff; background:#505050; }
            QToolButton:pressed { background:#007acc; }
        """)
        self.addToolBar(tb)

        logo = QLabel("  <b><span style='color:#007acc;font-family:Consolas;font-size:14px;'>PyRep</span></b>  ")
        logo.setTextFormat(Qt.TextFormat.RichText)
        tb.addWidget(logo)
        tb.addSeparator()

        for label, shortcut, slot in [
            ("📄 Yeni",   "Ctrl+N",       self._new_file),
            ("📂 Aç",     "Ctrl+O",       self._open_file),
            ("💾 Kaydet", "Ctrl+S",       self._save_file),
            ("▶ Çalıştır","Ctrl+Return",  self._run_code),
            ("⏹ Durdur",  "",             self._stop_code),
        ]:
            act = QAction(label, self)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()

        pkg_act = QAction("📦 Kütüphaneler", self)
        pkg_act.triggered.connect(self._open_package_manager)
        tb.addAction(pkg_act)

        search_act = QAction("🔍 Ara (Ctrl+Shift+F)", self)
        search_act.setShortcut(QKeySequence("Ctrl+Shift+F"))
        search_act.triggered.connect(self._open_global_search)
        tb.addAction(search_act)

        # Ctrl+F
        find_act = QAction("Editörde Bul", self)
        find_act.setShortcut(QKeySequence("Ctrl+F"))
        find_act.triggered.connect(self._toggle_search_bar)
        self.addAction(find_act)

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.setStyleSheet("""
            QStatusBar { background:#007acc; color:#fff;
                         font-family:Consolas; font-size:10px; border-top:none; }
        """)
        self.setStatusBar(sb)
        self.status_label = QLabel("● Hazır")
        self.status_label.setStyleSheet("color:#fff; padding:0 8px;")
        sb.addWidget(self.status_label)
        self.cursor_label = QLabel("Satır 1, Sütun 1")
        self.cursor_label.setStyleSheet("color:#fff; padding:0 8px;")
        sb.addPermanentWidget(self.cursor_label)
        self.editor.cursorPositionChanged.connect(self._update_cursor_pos)

    def _load_default_code(self):
        self.editor.setPlainText(
            "# PyRep'e hoş geldin! 🎉\n"
            "# Ctrl+Enter   → Çalıştır\n"
            "# Ctrl+F       → Editörde Ara\n"
            "# Ctrl+Shift+F → Genel Arama\n\n"
            "def merhaba(isim):\n"
            '    print(f"Merhaba, {isim}! 👋")\n\n'
            'isimler = ["Ahmet", "Mehmet", "Ayşe"]\n'
            "for isim in isimler:\n"
            "    merhaba(isim)\n"
        )

    def _toggle_search_bar(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
        else:
            self.search_bar.show_and_focus()

    def _open_global_search(self):
        GlobalSearchDialog(self.file_explorer.root_path, self).exec()

    def _new_file(self):
        self.editor.clear()
        self.current_file = None
        self.tab_widget.setTabText(self.tab_widget.currentIndex(), "🐍 yeni.py")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "Python (*.py);;Tümü (*)")
        if path:
            self._load_file(path)

    def _load_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                self.editor.setPlainText(f.read())
            self.current_file = path
            self.tab_widget.setTabText(self.tab_widget.currentIndex(),
                                       f"🐍 {os.path.basename(path)}")
            self.status_label.setText(f"● {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _open_file_from_explorer(self, path):
        self._load_file(path)

    def _save_file(self):
        if self.current_file:
            self._write_file(self.current_file)
        else:
            self._save_as()

    def _save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Farklı Kaydet", "main.py", "Python (*.py);;Tümü (*)")
        if path:
            self._write_file(path)
            self.current_file = path
            self.tab_widget.setTabText(self.tab_widget.currentIndex(),
                                       f"🐍 {os.path.basename(path)}")

    def _write_file(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.status_label.setText(f"● Kaydedildi: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Kaydetme Hatası", str(e))

    def _close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)

    def _run_code(self):
        if self.run_thread and self.run_thread.isRunning():
            return
        self.terminal.clear()
        self._print_terminal("▶ Çalıştırılıyor...\n", "#007acc")
        self.status_label.setText("● Çalışıyor...")
        self.run_thread = RunThread(self.editor.toPlainText())
        self.run_thread.output.connect(lambda s: self._print_terminal(s, "#cccccc"))
        self.run_thread.error.connect(lambda s: self._print_terminal(s, "#f44747"))
        self.run_thread.finished.connect(self._on_run_finished)
        self.run_thread.start()
        self.main_tabs.setCurrentIndex(0)

    def _stop_code(self):
        if self.run_thread and self.run_thread.isRunning():
            self.run_thread.terminate()
            self._print_terminal("\n⏹ Durduruldu.", "#dcdcaa")

    def _on_run_finished(self, code):
        if code == 0:
            self._print_terminal("\n✅ Tamamlandı.", "#4ec9b0")
            self.status_label.setText("● Tamamlandı")
        else:
            self._print_terminal(f"\n❌ Hata kodu: {code}", "#f44747")
            self.status_label.setText("● Hata")

    def _run_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        self._print_terminal(f"$ {cmd}", "#4ec9b0")
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                cwd=self.file_explorer.root_path
            )
            stdout, stderr = proc.communicate(timeout=30)
            if stdout:
                for line in stdout.splitlines():
                    self._print_terminal(line, "#cccccc")
            if stderr:
                for line in stderr.splitlines():
                    self._print_terminal(line, "#f44747")
        except subprocess.TimeoutExpired:
            self._print_terminal("⏰ Zaman aşımı (30s)", "#dcdcaa")
        except Exception as e:
            self._print_terminal(str(e), "#f44747")

    def _print_terminal(self, text: str, color: str = "#cccccc"):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(text + "\n", fmt)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

    def _open_package_manager(self):
        PackageManagerDialog(self).exec()

    def _update_cursor_pos(self):
        c = self.editor.textCursor()
        self.cursor_label.setText(f"Satır {c.blockNumber()+1}, Sütun {c.columnNumber()+1}")