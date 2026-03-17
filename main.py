"""
PyRep - Python IDE
Başlatmak için: python main.py

Gerekli kurulum:
    pip install PyQt6 PyQt6-QScintilla
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt
from editor import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PyRep")
    app.setStyle("Fusion")

    # Genel font
    font = QFont("Consolas", 10)
    app.setFont(font)

    # Koyu tema (palette)
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor("#d4d4d4"))
    palette.setColor(QPalette.ColorRole.Base,            QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor("#252526"))
    palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor("#252526"))
    palette.setColor(QPalette.ColorRole.ToolTipText,     QColor("#d4d4d4"))
    palette.setColor(QPalette.ColorRole.Text,            QColor("#d4d4d4"))
    palette.setColor(QPalette.ColorRole.Button,          QColor("#252526"))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor("#d4d4d4"))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor("#007acc"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()