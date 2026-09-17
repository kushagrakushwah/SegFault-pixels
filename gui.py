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
    window = QApp()
    window.setWindowTitle('PTA-Viz — Interactive Pointer Analysis Visualizer')
    window.resize(1800, 950)
    window.show()
    sys.exit(app.exec())
