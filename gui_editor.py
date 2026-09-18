from PyQt6.QtCore import Qt, QRect
from PyQt6.QtWidgets import (QWidget, QTextEdit, QPlainTextEdit, QHBoxLayout,
                              QVBoxLayout, QFileDialog)
from PyQt6.QtGui import QColor, QPainter, QFont, QTextFormat, QTextCursor
from guiHelper import QPushButton, QAlgoButton, QSpinBox, QLabel, QL

# Default interprocedural example: global pointer flows through alloc()
# alloc() is the callee; main() is caller; g is the global pointer
DEFAULT_PROGRAM = "structs:\nNode{Node* next\n}\nglobals:\nNode* g\nfuncs:\nalloc() {\nNode* t\nt = malloc()\ng = t\n}\nmain:\nNode* a\nNode* b\ncall alloc()\na = g\nb = a\nuse b\n"


class QCodeEditor(QPlainTextEdit):
    class NumberBar(QWidget):
        def __init__(self, editor):
            QWidget.__init__(self, editor)
            self.editor = editor
            self.line_count = 1
            self.updateWidth(1)
            self.editor.blockCountChanged.connect(self.updateWidth)
            self.editor.updateRequest.connect(self.updateContents)
            self.font = QFont()
            self.numberBarColor = QColor("#e8e8e8")

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.fillRect(event.rect(), self.numberBarColor)
            block = self.editor.firstVisibleBlock()
            while block.isValid():
                blockNumber = block.blockNumber()
                block_top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
                if not block.isVisible() or block_top >= event.rect().bottom():
                    break
                if blockNumber == self.editor.textCursor().blockNumber():
                    self.font.setBold(True)
                    painter.setPen(QColor("#000000"))
                else:
                    self.font.setBold(False)
                    painter.setPen(QColor("#717171"))
                painter.setFont(self.font)
                paint_rect = QRect(0, int(block_top), int(self.width())-5, int(self.editor.fontMetrics().height()))
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight, str(blockNumber+1))
                block = block.next()
            painter.end()
            QWidget.paintEvent(self, event)

        def getWidth(self):
            return self.fontMetrics().horizontalAdvance(str(self.line_count)) + 10

        def updateWidth(self, line_count):
            self.line_count = line_count
            width = self.getWidth()
            if self.width() != width:
                self.setFixedWidth(width)
                self.editor.setViewportMargins(width, 0, 0, 0)

        def updateFont(self):
            self.updateWidth(self.line_count)

        def updateContents(self, rect, scroll):
            if scroll:
                self.scroll(0, scroll)
            else:
                self.update(0, rect.y(), self.width(), rect.height())

    def __init__(self, font=QFont("Consolas", 12)):
        super(QCodeEditor, self).__init__()
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.numberBar = self.NumberBar(self)
        self.currentLineNumber = None
        self.blockHeight = None
        self.currentLineColor = QColor(255, 255, 180)  # light yellow on white bg
        self.cursorPositionChanged.connect(self.highligtCurrentLine)

    def resizeEvent(self, *e):
        cr = self.contentsRect()
        rec = QRect(cr.left(), cr.top(), self.numberBar.getWidth(), cr.height())
        self.numberBar.setGeometry(rec)
        QPlainTextEdit.resizeEvent(self, *e)

    def focusInEvent(self, e):
        self.highligtCurrentLine()
        QPlainTextEdit.focusInEvent(self, e)

    def focusOutEvent(self, e):
        self.currentLineNumber = None
        self.setExtraSelections([])
        QPlainTextEdit.focusOutEvent(self, e)

    def highligtCurrentLine(self):
        newCurrentLineNumber = self.textCursor().blockNumber()
        newBlockHeight = self.blockBoundingRect(self.textCursor().block()).height()
        if newCurrentLineNumber != self.currentLineNumber or self.blockHeight != newBlockHeight:
            self.currentLineNumber = newCurrentLineNumber
            self.blockHeight = newBlockHeight
            temp_cursor = QTextCursor(self.textCursor().block())
            hi_selections = []
            hi_selection = QTextEdit.ExtraSelection()
            hi_selection.format.setBackground(self.currentLineColor)
            hi_selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            hi_selection.cursor = temp_cursor
            hi_selections.append(hi_selection)
            check = temp_cursor.movePosition(QTextCursor.MoveOperation.Down)
            while check and not temp_cursor.atBlockStart():
                hi_selection = QTextEdit.ExtraSelection(hi_selection)
                hi_selection.cursor = temp_cursor
                hi_selections.append(hi_selection)
                check = temp_cursor.movePosition(QTextCursor.MoveOperation.Down)
            self.setExtraSelections(hi_selections)

    def updateFont(self, newFont):
        self.setFont(newFont)
        self.numberBar.updateFont()


class QCodeEditorWindow(QWidget):
    def __init__(self, parentAnalyzeFunc, algoChangeFunc):
        super(QWidget, self).__init__()
        self.filePath = ''
        self.text = ''
        self.parentAnalyzeFunc = parentAnalyzeFunc
        self.algoChangeFunc = algoChangeFunc

        initialFontSize = 13
        self.editorFont = QFont("Consolas", initialFontSize)
        self.editor = QCodeEditor(self.editorFont)
        self.editor.textChanged.connect(self.updateSaveButton)
        self.editor.setPlainText(DEFAULT_PROGRAM)
        self.text = DEFAULT_PROGRAM

        self.openButton    = QPushButton('Open IR', self.openFile,   self)
        self.loadCButton   = QPushButton('Load C',  self.loadCFile,  self)
        self.saveButton    = QPushButton('Save',    self.saveFile,   self)
        self.saveAsButton  = QPushButton('Save As', self.saveAsFile, self)
        self.analyzeButton = QPushButton('Analyze', self.analyze,    self)
        self.saveButton.setEnabled(False)
        self.loadCButton.setToolTip('Convert a .c file to PTA-Viz IR and load it for analysis')

        self.zoomText    = QL('Font:')
        self.zoomSpinBox = QSpinBox(self.updateFontSize, initialFontSize, 5, 150, parent=self)

        fileBar = QHBoxLayout()
        fileBar.addWidget(self.openButton)
        fileBar.addWidget(self.loadCButton)
        fileBar.addWidget(self.saveButton)
        fileBar.addWidget(self.saveAsButton)
        fileBar.addWidget(self.analyzeButton)
        fileBar.addStretch()
        fileBar.addWidget(self.zoomText)
        fileBar.addWidget(self.zoomSpinBox)

        # Algorithm selector buttons
        algos = [
            ("Andersen's",     'andersens'),
            ("Steensgaard's",  'steensgaards'),
            ("FS-PTA",         'fspta'),
            ("VASCO",          'vasco'),
            ("LFCPA",          'lfcpa'),
        ]
        self.algoButtons = {}
        algoBar = QHBoxLayout()
        algoBar.addWidget(QL('Algorithm:'))
        for label, key in algos:
            btn = QAlgoButton(label, lambda checked, k=key: self.algoChangeFunc(k), self)
            self.algoButtons[key] = btn
            algoBar.addWidget(btn)
        algoBar.addStretch()
        self.algoButtons['andersens'].setChecked(True)

        self.errorMessage = QL('')
        self.errorMessage.setStyleSheet("QLabel { background-color: #ffd6d6; color: #8b0000; padding: 4px; }")
        self.errorMessage.setWordWrap(True)
        self.errorMessage.hide()

        self.vBox = QVBoxLayout()
        self.vBox.addLayout(fileBar)
        self.vBox.addLayout(algoBar)
        self.vBox.addWidget(self.editor)
        self.vBox.addWidget(self.errorMessage)
        self.setLayout(self.vBox)
        self.vBox.setContentsMargins(4,4,4,4)

    def setActiveAlgo(self, key):
        for k, btn in self.algoButtons.items():
            btn.setChecked(k == key)

    def openFile(self):
        newFilePath = QFileDialog.getOpenFileName(self, 'Open IR file', '', 'PTA-Viz IR (*.txt);;All files (*)')[0]
        if newFilePath and newFilePath != self.filePath:
            try:
                with open(newFilePath, 'r') as f:
                    self.text = f.read()
                self.filePath = newFilePath
                self.editor.setPlainText(self.text)
                self.saveButton.setEnabled(False)
            except:
                pass

    def loadCFile(self):
        """Open a .c file, convert to PTA-Viz IR, and load into editor."""
        cFilePath = QFileDialog.getOpenFileName(self, 'Load C file', '', 'C files (*.c *.h);;All files (*)')[0]
        if not cFilePath:
            return
        try:
            from c_to_ir import convert_c_to_ir
            with open(cFilePath, 'r') as f:
                c_code = f.read()
            ir = convert_c_to_ir(c_code)
            self.editor.setPlainText(ir)
            self.text = ir
            self.filePath = None
            self.saveButton.setEnabled(False)
            self.errorMessage.setText(f'C file converted: {cFilePath}')
            self.errorMessage.setStyleSheet('QLabel { background-color: #d6ffd6; color: #005500; padding: 4px; }')
            self.errorMessage.show()
        except Exception as e:
            self.errorMessage.setText(f'C conversion error: {e}')
            self.errorMessage.setStyleSheet('QLabel { background-color: #ffd6d6; color: #8b0000; padding: 4px; }')
            self.errorMessage.show()

    def updateSaveButton(self):
        if self.filePath:
            self.saveButton.setEnabled(self.text != self.editor.toPlainText())

    def saveFile(self):
        try:
            editorText = self.editor.toPlainText()
            with open(self.filePath, 'w') as f:
                f.write(editorText)
            self.text = editorText
            self.saveButton.setEnabled(False)
        except:
            pass

    def saveAsFile(self):
        newFilePath = QFileDialog.getSaveFileName(self, 'Save as file')[0]
        if newFilePath:
            try:
                editorText = self.editor.toPlainText()
                with open(newFilePath, 'w') as f:
                    f.write(editorText)
                self.filePath = newFilePath
                self.text = editorText
                self.saveButton.setEnabled(False)
            except:
                pass

    def updateFontSize(self, newFontSize):
        self.editorFont.setPointSize(newFontSize)
        self.editor.updateFont(self.editorFont)

    def analyze(self):
        import io, sys
        from main import perform_analysis
        self.errorMessage.hide()
        self.errorMessage.setText('')

        # Capture terminal output during analysis
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            err = perform_analysis(self.editor.toPlainText())
        finally:
            sys.stdout = old_stdout

        log = captured.getvalue().strip()

        if err:
            self.errorMessage.setText('Error: ' + err)
            self.errorMessage.show()
        else:
            self.parentAnalyzeFunc(log)
