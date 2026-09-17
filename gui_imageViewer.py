from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                              QScrollArea, QStackedWidget, QPlainTextEdit)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PyQt6.QtSvgWidgets import QSvgWidget
from guiHelper import QSpinBox, QPushButton, QTextWidget, QLabel, QSplitter
from helper import get_points_to_graph_from_file
import json, os

# ── Scrollable SVG Image ─────────────────────────────────────────────────────

class QScrollableImage(QScrollArea):

    class QImage(QSvgWidget):
        def __init__(self, clickable=False, stmtChangeFunc=None):
            QSvgWidget.__init__(self)
            self.mag = 1
            self.hi = None
            self.posDict = {}
            if clickable:
                self.mousePressEvent = self.getPos
                self.stmtChangeFunc = stmtChangeFunc

        def paintEvent(self, event):
            QSvgWidget.paintEvent(self, event)
            if self.hi is not None:
                painter = QPainter(self)
                brush = QBrush(QColor(0, 0, 255, 50))
                painter.setBrush(brush)
                pen = QPen(Qt.GlobalColor.blue, 4)
                painter.setPen(pen)
                painter.scale(self.mag, self.mag)
                if self.hi in self.posDict:
                    painter.drawRect(self.posDict[self.hi])
                painter.end()

        def getPos(self, event):
            x = round(event.pos().x()/self.mag)
            y = round(event.pos().y()/self.mag)
            for key, bb in self.posDict.items():
                if bb.contains(x, y):
                    if key != self.hi:
                        self.hi = key
                        self.repaint()
                        if hasattr(self, 'stmtChangeFunc'):
                            self.stmtChangeFunc(key)
                    return
            if self.hi is not None:
                self.hi = None
                self.repaint()

        def setMagnification(self, mag):
            self.mag = mag
            self.resize(self.initSize*mag)

        def setImage(self, imgPath):
            if isinstance(imgPath, str):
                self.renderer().load(imgPath)
            else:
                self.renderer().load(imgPath)
            self.initSize = self.renderer().defaultSize()
            self.resize(self.initSize*self.mag)

        def setData(self, img, posDict, hi):
            self.setImage(img)
            self.posDict.clear()
            self.hi = None
            img_height = self.initSize.height()
            for key, pd in posDict.items():
                self.posDict[key] = QRect(pd['x'], img_height-pd['y']+1, pd['w'], pd['h'])

        def setHi(self, hi):
            self.hi = hi
            self.repaint()

    def __init__(self, clickable=False, stmtChangeFunc=None):
        QScrollArea.__init__(self)
        self.image = self.QImage(clickable, stmtChangeFunc)
        self.setWidget(self.image)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def setScale(self, mag):
        self.image.setMagnification(mag/100)

    def resetImage(self, img):
        self.image.setImage(img)

    def resetData(self, img, posDict, hi=None):
        self.image.setData(img, posDict, hi)

    def setHi(self, hi):
        self.image.setHi(hi)


# ── CFG Window (clickable) ────────────────────────────────────────────────────

class QCFGWindow(QWidget):
    def __init__(self, stmtChangeFunc, clickable=True):
        super(QWidget, self).__init__()
        self.imageViewer = QScrollableImage(clickable, stmtChangeFunc)
        self.zoomText = QLabel('Zoom:')
        self.zoomSpinBox = QSpinBox(self.imageViewer.setScale, 100, 30, 500, 10, self)
        self.zoomSpinBox.setSuffix('%')
        self.zoomSpinBox.setAccelerated(True)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('CFG'))
        controls.addStretch()
        controls.addWidget(self.zoomText)
        controls.addWidget(self.zoomSpinBox)
        vBox = QVBoxLayout()
        vBox.addLayout(controls)
        vBox.addWidget(self.imageViewer)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def resetData(self, img, posDict, hi=None):
        self.imageViewer.resetData(img, posDict, None)

    def setHighlight(self, hi):
        self.imageViewer.setHi(hi)


# ── Single PTA graph panel ────────────────────────────────────────────────────

class QPTAWindow(QWidget):
    def __init__(self, infoText='PTA'):
        super(QWidget, self).__init__()
        self.imageViewer = QScrollableImage()
        self.infoText = QLabel(infoText)
        self.zoomText = QLabel('Zoom:')
        self.zoomSpinBox = QSpinBox(self.imageViewer.setScale, 100, 30, 500, 10, self)
        self.zoomSpinBox.setSuffix('%')
        self.zoomSpinBox.setAccelerated(True)
        controls = QHBoxLayout()
        controls.addWidget(self.infoText)
        controls.addStretch()
        controls.addWidget(self.zoomText)
        controls.addWidget(self.zoomSpinBox)
        vBox = QVBoxLayout()
        vBox.addLayout(controls)
        vBox.addWidget(self.imageViewer)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def resetImage(self, data):
        """data: svg bytes or file path string"""
        self.imageViewer.resetImage(data)

    def resetFromJson(self, jsonPath):
        if os.path.exists(jsonPath):
            self.imageViewer.resetImage(get_points_to_graph_from_file(jsonPath))

    def resetFromSvg(self, svgPath):
        if os.path.exists(svgPath):
            with open(svgPath, 'rb') as f:
                self.imageViewer.resetImage(f.read())


# ── Andersen's widget (FI, per-iteration) ────────────────────────────────────

class QAndersensWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.basePath = ''
        self.numIters = 0

        self.iterLabel = QLabel("Iteration:")
        self.iterBox = QSpinBox(self._onIterChange, 0, 0, 0, 1, self)
        self.iterCountLabel = QLabel("/ 0")
        self.graphView = QPTAWindow("Points-to Graph (Andersen's)")

        topBar = QHBoxLayout()
        topBar.addWidget(self.iterLabel)
        topBar.addWidget(self.iterBox)
        topBar.addWidget(self.iterCountLabel)
        topBar.addStretch()

        vBox = QVBoxLayout()
        vBox.addLayout(topBar)
        vBox.addWidget(self.graphView)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def setData(self, basePath, numIters):
        self.basePath = basePath
        self.numIters = numIters
        self.iterCountLabel.setText("/ %d" % numIters)
        self.iterBox.resetValues(numIters, 0, numIters)
        self._onIterChange(numIters)

    def _onIterChange(self, val):
        path = self.basePath + 'pta/iter_%d.json' % val
        self.graphView.resetFromJson(path)


# ── Steensgaard's widget (final graph) ───────────────────────────────────────

class QSteensgaardsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.iterLabel = QLabel("Iterations: —")
        self.graphView = QPTAWindow("Equivalence-class graph (Steensgaard's)")
        topBar = QHBoxLayout()
        topBar.addWidget(self.iterLabel)
        topBar.addStretch()
        vBox = QVBoxLayout()
        vBox.addLayout(topBar)
        vBox.addWidget(self.graphView)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def setData(self, basePath, numIters):
        self.iterLabel.setText("Convergence in %d iterations" % numIters)
        svgPath = basePath + 'pta/final.svg'
        self.graphView.resetFromSvg(svgPath)


# ── Flow-Sensitive PTA widget ─────────────────────────────────────────────────

class QFSPTAWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.basePath = ''
        self.numIters = 0
        self.currStmt = 0

        self.iterLabel = QLabel("Iteration:")
        self.iterBox = QSpinBox(self._onIterChange, 1, 1, 1, 1, self)
        self.iterCountLabel = QLabel("/ 0")

        self.inView  = QPTAWindow("IN  (before stmt)")
        self.outView = QPTAWindow("OUT (after stmt)")
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.inView)
        split.addWidget(self.outView)

        topBar = QHBoxLayout()
        topBar.addWidget(self.iterLabel)
        topBar.addWidget(self.iterBox)
        topBar.addWidget(self.iterCountLabel)
        topBar.addStretch()

        vBox = QVBoxLayout()
        vBox.addLayout(topBar)
        vBox.addWidget(split)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def setData(self, basePath, numIters):
        self.basePath = basePath
        self.numIters = numIters
        self.iterCountLabel.setText("/ %d" % numIters)
        self.iterBox.resetValues(1, 1, numIters)
        self._onIterChange(1)

    def setCurrStmt(self, stmt):
        self.currStmt = stmt
        self._onIterChange(self.iterBox.value())

    def _onIterChange(self, val):
        base = self.basePath + 'pta/iter_%dstmt_%d_' % (val, self.currStmt)
        self.inView.resetFromJson(base + 'in.json')
        self.outView.resetFromJson(base + 'out.json')


# ── VASCO widget (FS+CS) ──────────────────────────────────────────────────────

class QVASCOWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.basePath = ''
        self.numIters = 0
        self.currStmt = 0

        self.iterLabel = QLabel("Iteration:")
        self.iterBox = QSpinBox(self._onIterChange, 1, 1, 1, 1, self)
        self.iterCountLabel = QLabel("/ 0")

        self.outView = QPTAWindow("Points-to state (VASCO)")
        self.contextLog = QTextWidget("Context Log")
        self.contextLog.setMaximumWidth(320)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.outView)
        split.addWidget(self.contextLog)

        topBar = QHBoxLayout()
        topBar.addWidget(self.iterLabel)
        topBar.addWidget(self.iterBox)
        topBar.addWidget(self.iterCountLabel)
        topBar.addStretch()

        vBox = QVBoxLayout()
        vBox.addLayout(topBar)
        vBox.addWidget(split)
        self.setLayout(vBox)
        vBox.setContentsMargins(0,0,0,0)

    def setData(self, basePath, numIters):
        self.basePath = basePath
        self.numIters = numIters
        self.iterCountLabel.setText("/ %d" % numIters)
        self.iterBox.resetValues(1, 1, numIters)
        self._loadContextLog(basePath)
        self._onIterChange(1)

    def _loadContextLog(self, basePath):
        logPath = basePath + 'context_log.json'
        if os.path.exists(logPath):
            with open(logPath) as f:
                d = json.load(f)
            log = d.get('log', [])
            self.contextLog.editor.setPlainText('\n'.join(log))

    def setCurrStmt(self, stmt):
        self.currStmt = stmt
        self._onIterChange(self.iterBox.value())

    def _onIterChange(self, val):
        path = self.basePath + 'pta/iter_%dstmt_%d_out.json' % (val, self.currStmt)
        self.outView.resetFromJson(path)


# ── LFCPA widget (kept from original) ────────────────────────────────────────

class QLFCPAWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.LivenessFp = './results/lfcpa/la/iter_'
        self.PTAFp = './results/lfcpa/pta/iter_'
        self.currIter = -1
        self.currStmt = -1
        self.rounds = -1
        self.PTAAnalysis = True

        self.PTAinNext  = QPTAWindow("PTA in (new)")
        self.PTAoutNext = QPTAWindow("PTA out (new)")
        self.PTAResults = QSplitter(Qt.Orientation.Horizontal)
        self.PTAResults.addWidget(self.PTAinNext)
        self.PTAResults.addWidget(self.PTAoutNext)

        self.LinNext  = QTextWidget("Liveness in (new)")
        self.LoutNext = QTextWidget("Liveness out (new)")
        self.LResults = QSplitter(Qt.Orientation.Horizontal)
        self.LResults.addWidget(self.LinNext)
        self.LResults.addWidget(self.LoutNext)

        self.PTAinOld  = QPTAWindow("PTA in (prev)")
        self.PTAoutOld = QPTAWindow("PTA out (prev)")
        PTAOld = QSplitter(Qt.Orientation.Horizontal)
        PTAOld.addWidget(self.PTAinOld)
        PTAOld.addWidget(self.PTAoutOld)

        self.LinOld  = QTextWidget("Liveness in (prev)")
        self.LoutOld = QTextWidget("Liveness out (prev)")
        LOld = QSplitter(Qt.Orientation.Horizontal)
        LOld.addWidget(self.LinOld)
        LOld.addWidget(self.LoutOld)

        self.dataSplitter = QSplitter(Qt.Orientation.Vertical)
        self.dataSplitter.addWidget(self.PTAResults)
        self.dataSplitter.addWidget(PTAOld)
        self.dataSplitter.addWidget(LOld)

        self.iterSpinBox  = QSpinBox(self.changeIter,  -1, -1, -1, parent=self)
        self.roundSpinBox = QSpinBox(self.changeRound, -1, -1, -1, parent=self)
        self.switchAnalysisButton = QPushButton('PTA', self.switchAnalysisType, self)

        iterControl = QHBoxLayout()
        iterControl.addWidget(QLabel('Iteration:'))
        iterControl.addWidget(self.iterSpinBox)
        iterControl.addSpacing(20)
        iterControl.addWidget(QLabel('Round:'))
        iterControl.addWidget(self.roundSpinBox)
        iterControl.addStretch()
        iterControl.addWidget(self.switchAnalysisButton)

        viewer = QVBoxLayout()
        viewer.addLayout(iterControl)
        viewer.addWidget(self.dataSplitter)
        self.setLayout(viewer)
        viewer.setContentsMargins(0,0,0,0)

    def getPath(self, iter, round, stmt):
        return str(iter)+'_'+str(round)+'stmt_'+str(stmt)

    def changeIter(self, newIter):
        self.roundSpinBox.resetValues(1, 1, self.rounds[newIter-1][1])
        self.currIter = newIter
        self.changeRound(1)

    def changeRound(self, newRound):
        if self.PTAAnalysis:
            self.PTAinNext.resetFromJson(self.PTAFp + self.getPath(self.currIter, newRound, self.currStmt) + '_in.json')
            self.PTAoutNext.resetFromJson(self.PTAFp + self.getPath(self.currIter, newRound, self.currStmt) + '_out.json')
            self.PTAinOld.resetFromJson(self.PTAFp + self.getPath(self.currIter, newRound-1, self.currStmt) + '_in.json')
            self.PTAoutOld.resetFromJson(self.PTAFp + self.getPath(self.currIter, newRound-1, self.currStmt) + '_out.json')
            self.LinOld.setText(self.LivenessFp + self.getPath(self.currIter, self.rounds[self.currIter-1][0], self.currStmt) + '_in.json')
            self.LoutOld.setText(self.LivenessFp + self.getPath(self.currIter, self.rounds[self.currIter-1][0], self.currStmt) + '_out.json')
        else:
            self.PTAinOld.resetFromJson(self.PTAFp + self.getPath(self.currIter, 0, self.currStmt) + '_in.json')
            self.PTAoutOld.resetFromJson(self.PTAFp + self.getPath(self.currIter, 0, self.currStmt) + '_out.json')
            self.LinNext.setText(self.LivenessFp + self.getPath(self.currIter, newRound, self.currStmt) + '_in.json')
            self.LoutNext.setText(self.LivenessFp + self.getPath(self.currIter, newRound, self.currStmt) + '_out.json')
            self.LinOld.setText(self.LivenessFp + self.getPath(self.currIter, newRound-1, self.currStmt) + '_in.json')
            self.LoutOld.setText(self.LivenessFp + self.getPath(self.currIter, newRound-1, self.currStmt) + '_out.json')

    def setData(self, iters):
        self.rounds = iters
        self.currIter = 1
        self.currStmt = 0
        self.PTAAnalysis = True
        self.switchAnalysisType()
        self.roundSpinBox.resetValues(1, 1, self.rounds[0][1])
        self.iterSpinBox.resetValues(1, 1, len(iters))
        self.changeIter(1)

    def switchAnalysisType(self):
        self.PTAAnalysis = not self.PTAAnalysis
        if self.PTAAnalysis:
            self.roundSpinBox.resetValues(1, 1, self.rounds[self.currIter-1][1])
            self.switchAnalysisButton.setText('PTA')
            self.dataSplitter.replaceWidget(0, self.PTAResults)
        else:
            self.roundSpinBox.resetValues(1, 1, self.rounds[self.currIter-1][0])
            self.switchAnalysisButton.setText('LA')
            self.dataSplitter.replaceWidget(0, self.LResults)
        self.roundSpinBox.setValue(1)
        self.changeRound(1)

    def setCurrStmt(self, stmt):
        self.currStmt = stmt
        self.changeRound(self.roundSpinBox.value())
