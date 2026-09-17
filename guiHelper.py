from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QPushButton as QPB, QWidget, QSpinBox as QSB,
                              QPlainTextEdit as QPTE, QLabel as QL,
                              QHBoxLayout, QVBoxLayout, QSplitter as QS,
                              QButtonGroup, QSizePolicy)
from PyQt6.QtGui import QFont
import json

class QPushButton(QPB):
    def __init__(self, text, onClickFunc, parent=None):
        QPB.__init__(self, text, parent)
        self.clicked.connect(onClickFunc)
        self.setFixedHeight(self.height())
        self.setFixedWidth(90)

class QAlgoButton(QPB):
    """Wider toggle button for algorithm selector."""
    def __init__(self, text, onClickFunc, parent=None):
        QPB.__init__(self, text, parent)
        self.clicked.connect(onClickFunc)
        self.setCheckable(True)
        self.setFixedHeight(28)
        self.setMinimumWidth(110)

class QSpinBox(QSB):
    def __init__(self, valChangeFunc, initialValue=50, minValue=0, maxValue=100, stepSize=1, parent=None):
        QSB.__init__(self, parent)
        self.setMinimum(minValue)
        self.setMaximum(maxValue)
        self.setValue(initialValue)
        self.setSingleStep(stepSize)
        self.setFixedHeight(self.height())
        self.setFixedWidth(70)
        self.valueChanged.connect(valChangeFunc)

    def resetValues(self, initialValue=1, minValue=1, maxValue=100):
        self.blockSignals(True)
        self.setMinimum(minValue)
        self.setMaximum(maxValue)
        self.setValue(initialValue)
        self.blockSignals(False)

class QSplitter(QS):
    # BUG C FIX: accept orientation as first arg
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        QS.__init__(self, orientation, parent)
        self.setHandleWidth(8)

class QLabel(QL):
    def __init__(self, text, parent=None):
        QL.__init__(self, text, parent)

class QTextWidget(QWidget):
    class QText(QPTE):
        def __init__(self, font):
            QPTE.__init__(self)
            self.setDisabled(True)
            self.setFont(font)

        def setText(self, filePath):
            try:
                with open(filePath) as fp:
                    d = json.load(fp)
                    if len(d) == 0:
                        self.setPlainText("(empty)")
                    else:
                        self.setPlainText("\n".join(ptr+': '+(', '.join(str(x) for x in flds)) for ptr, flds in d.items()))
            except Exception as e:
                self.setPlainText("(no data)")

        def updateFont(self, newFont):
            self.setFont(newFont)

    def __init__(self, infoText=''):
        QWidget.__init__(self)
        initialFontSize = 12
        self.editorFont = QFont("Consolas", initialFontSize)
        self.editor = self.QText(self.editorFont)
        self.zoomText = QLabel('Font:')
        self.zoomSpinBox = QSpinBox(self.updateFontSize, initialFontSize, 5, 150)
        self.infoText = QLabel(infoText)
        self.controls = QHBoxLayout()
        self.controls.addWidget(self.infoText)
        self.controls.addStretch()
        self.controls.addWidget(self.zoomText)
        self.controls.addWidget(self.zoomSpinBox)
        self.vBox = QVBoxLayout(self)
        self.vBox.addLayout(self.controls)
        self.vBox.addWidget(self.editor)
        self.vBox.setContentsMargins(0,0,0,0)
        self.setText = self.editor.setText

    def updateFontSize(self, newFontSize):
        self.editorFont.setPointSize(newFontSize)
        self.editor.updateFont(self.editorFont)
