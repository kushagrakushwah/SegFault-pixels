from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                              QApplication, QStackedWidget, QSizePolicy, QLabel)
from PyQt6.QtGui import QFont
from guiHelper import QSplitter
from gui_imageViewer import (QLFCPAWidget, QCFGWindow,
                              QAndersensWidget, QSteensgaardsWidget,
                              QFSPTAWidget, QVASCOWidget)
from gui_editor import QCodeEditorWindow
import sys, json, os

ALGO_ORDER = ['andersens', 'steensgaards', 'fspta', 'vasco', 'lfcpa']
ALGO_INDEX = {k: i for i, k in enumerate(ALGO_ORDER)}

class QApp(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.currAlgo = 'andersens'
        self.currStmt = 0

        # Right-side result widgets (one per algo)
        self.andersensWidget    = QAndersensWidget()
        self.steensgaardsWidget = QSteensgaardsWidget()
        self.fsPTAWidget        = QFSPTAWidget()
        self.vascoWidget        = QVASCOWidget()
        self.lfcpaWidget        = QLFCPAWidget()

        self.resultStack = QStackedWidget()
        self.resultStack.addWidget(self.andersensWidget)     # 0
        self.resultStack.addWidget(self.steensgaardsWidget)  # 1
        self.resultStack.addWidget(self.fsPTAWidget)         # 2
        self.resultStack.addWidget(self.vascoWidget)         # 3
        self.resultStack.addWidget(self.lfcpaWidget)         # 4

        # CFG window (middle panel)
        self.cfgWindow = QCFGWindow(self._onStmtClick)

        # Editor (left panel)
        self.editor = QCodeEditorWindow(self._onAnalyzeComplete, self._onAlgoChange)

        # Horizontal splitter: editor | cfg | results
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.cfgWindow)
        splitter.addWidget(self.resultStack)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 4)

        hbox = QHBoxLayout(self)
        hbox.addWidget(splitter)
        self.setLayout(hbox)
        hbox.setContentsMargins(4, 4, 4, 4)

    def _onAlgoChange(self, algo):
        self.currAlgo = algo
        self.editor.setActiveAlgo(algo)
        self.resultStack.setCurrentIndex(ALGO_INDEX[algo])
        # If results exist, reload them
        infoPath = './results/%s/info.json' % algo
        if os.path.exists(infoPath):
            self._loadResults(algo)

    def _onAnalyzeComplete(self):
        self._loadResults(self.currAlgo)

    def _loadResults(self, algo):
        infoPath = './results/%s/info.json' % algo
        if not os.path.exists(infoPath):
            return
        try:
            with open(infoPath) as f:
                infoDict = json.load(f)
        except Exception:
            return

        basePath = './results/%s/' % algo
        posDict  = infoDict.get('pos_dicts', {})
        codeSvg  = basePath + 'code.svg'

        # Load CFG
        if os.path.exists(codeSvg):
            self.cfgWindow.resetData(codeSvg, posDict)

        iters = infoDict.get('iters', 1)

        if algo == 'andersens':
            self.andersensWidget.setData(basePath, iters)
        elif algo == 'steensgaards':
            self.steensgaardsWidget.setData(basePath, iters)
        elif algo == 'fspta':
            self.fsPTAWidget.setData(basePath, iters)
        elif algo == 'vasco':
            self.vascoWidget.setData(basePath, iters)
        elif algo == 'lfcpa':
            self.lfcpaWidget.setData(iters)

    def _onStmtClick(self, stmt):
        self.currStmt = stmt
        algo = self.currAlgo
        if algo == 'fspta':
            self.fsPTAWidget.setCurrStmt(stmt)
        elif algo == 'vasco':
            self.vascoWidget.setCurrStmt(stmt)
        elif algo == 'lfcpa':
            self.lfcpaWidget.setCurrStmt(stmt)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # ── White / Light theme ──────────────────────────────────────────────────
    from PyQt6.QtGui import QPalette, QColor
    palette = QPalette()
    WHITE       = QColor(255, 255, 255)
    LIGHT_GRAY  = QColor(240, 240, 240)
    MID_GRAY    = QColor(200, 200, 200)
    DARK_TEXT   = QColor(20,  20,  20)
    BLUE_HI     = QColor(0,   120, 215)
    BLUE_TEXT   = QColor(255, 255, 255)
    PANEL_BG    = QColor(248, 248, 248)

    palette.setColor(QPalette.ColorRole.Window,          LIGHT_GRAY)
    palette.setColor(QPalette.ColorRole.WindowText,      DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Base,            WHITE)
    palette.setColor(QPalette.ColorRole.AlternateBase,   PANEL_BG)
    palette.setColor(QPalette.ColorRole.ToolTipBase,     WHITE)
    palette.setColor(QPalette.ColorRole.ToolTipText,     DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Text,            DARK_TEXT)
    palette.setColor(QPalette.ColorRole.Button,          LIGHT_GRAY)
    palette.setColor(QPalette.ColorRole.ButtonText,      DARK_TEXT)
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(200, 0, 0))
    palette.setColor(QPalette.ColorRole.Link,            BLUE_HI)
    palette.setColor(QPalette.ColorRole.Highlight,       BLUE_HI)
    palette.setColor(QPalette.ColorRole.HighlightedText, BLUE_TEXT)
    palette.setColor(QPalette.ColorRole.Mid,             MID_GRAY)
    palette.setColor(QPalette.ColorRole.Dark,            MID_GRAY)
    palette.setColor(QPalette.ColorRole.Shadow,          QColor(150, 150, 150))
    app.setPalette(palette)

    app.setStyleSheet("""
        QWidget          { background-color: #f8f8f8; color: #141414; }
        QPlainTextEdit   { background-color: #ffffff; color: #141414;
                           selection-background-color: #0078d7;
                           selection-color: #ffffff; }
        QScrollArea      { background-color: #ffffff; }
        QPushButton      { background-color: #e0e0e0; color: #141414;
                           border: 1px solid #b0b0b0; border-radius: 4px;
                           padding: 3px 8px; }
        QPushButton:hover       { background-color: #d0d0d0; }
        QPushButton:pressed     { background-color: #b8b8b8; }
        QPushButton:checked     { background-color: #0078d7; color: #ffffff;
                                  border: 1px solid #005fa3; }
        QSpinBox         { background-color: #ffffff; color: #141414;
                           border: 1px solid #b0b0b0; border-radius: 3px; }
        QLabel           { background-color: transparent; color: #141414; }
        QSplitter::handle { background-color: #c8c8c8; }
        QScrollBar:vertical   { background: #f0f0f0; width: 12px; }
        QScrollBar::handle:vertical { background: #b0b0b0; border-radius: 5px; }
        QScrollBar:horizontal { background: #f0f0f0; height: 12px; }
        QScrollBar::handle:horizontal { background: #b0b0b0; border-radius: 5px; }
    """)
    # ────────────────────────────────────────────────────────────────────────

    window = QApp()
    window.setWindowTitle('PTA-Viz — Interactive Pointer Analysis Visualizer')
    window.resize(1800, 950)
    window.show()
    sys.exit(app.exec())
