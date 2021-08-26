"""
Tool used for transferring weights between meshes using xml.
Using Python API 2.0.
"""
from collections import namedtuple
from time import gmtime, strftime
from PySide2 import QtCore, QtWidgets, QtGui

from dcc import fnskin
from dcc.userinterface import qproxywindow, iconutils

from .methods import pointcloud, inversedistance

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'selection'))


class QTransferWeights(qproxywindow.QProxyWindow):
    """
    Overload of QProxyWindow used for transferring skin weights between different meshes.
    """

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :keyword parent: QtWidgets.QWidget
        :keyword flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Declare private variables
        #
        self._clipboard = []
        self._methods = [pointcloud.PointCloud, inversedistance.InverseDistance]

        # Call parent method
        #
        super(QTransferWeights, self).__init__(*args, **kwargs)

    def __build__(self):
        """
        Private method used to build the user interface.

        :rtype: None
        """

        # Define window properties
        #
        self.setWindowTitle('|| Transfer Weights')
        self.setMinimumSize(QtCore.QSize(500, 250))

        # Create central widget
        #
        self.setCentralWidget(QtWidgets.QWidget())
        self.centralWidget().setLayout(QtWidgets.QVBoxLayout())

        # Define main layout
        #
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.centralWidget().layout().addWidget(self.splitter)

        # Create weights table widget
        #
        self.clipboardLayout = QtWidgets.QVBoxLayout()

        self.clipboardGroupBox = QtWidgets.QGroupBox('Clipboard:')
        self.clipboardGroupBox.setLayout(self.clipboardLayout)

        self.clipboardTableWidget = QtWidgets.QTableWidget()
        self.clipboardTableWidget.setShowGrid(True)
        self.clipboardTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.clipboardTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.clipboardTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.clipboardTableWidget.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.clipboardTableWidget.setColumnCount(4)
        self.clipboardTableWidget.setHorizontalHeaderLabels(['Name', 'Points', 'Date', ''])
        self.clipboardTableWidget.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.clipboardTableWidget.setColumnWidth(3, 40)
        self.clipboardTableWidget.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        self.clipboardTableWidget.horizontalHeader().setStretchLastSection(False)
        self.clipboardTableWidget.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.clipboardLayout.addWidget(self.clipboardTableWidget)

        self.splitter.addWidget(self.clipboardGroupBox)

        # Create method widgets
        #
        self.methodLayout = QtWidgets.QHBoxLayout()

        self.methodLabel = QtWidgets.QLabel('Method:')
        self.methodLabel.setFixedWidth(48)
        self.methodLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.methodComboBox = QtWidgets.QComboBox()
        self.methodComboBox.addItems([x.className for x in self._methods])

        self.methodLayout.addWidget(self.methodLabel)
        self.methodLayout.addWidget(self.methodComboBox)

        self.clipboardLayout.addLayout(self.methodLayout)

        # Create influences table widget
        #
        self.influenceLayout = QtWidgets.QVBoxLayout()

        self.influenceGroupBox = QtWidgets.QGroupBox('Influences:')
        self.influenceGroupBox.setLayout(self.influenceLayout)

        self.influenceListWidget = QtWidgets.QListWidget()
        self.influenceListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.influenceListWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.influenceLayout.addWidget(self.influenceListWidget)

        self.splitter.addWidget(self.influenceGroupBox)

        # Create buttons row
        #
        self.buttonLayout = QtWidgets.QHBoxLayout()

        self.extractButton = QtWidgets.QPushButton('Extract')
        self.extractButton.pressed.connect(self.extractWeights)

        self.applyBtn = QtWidgets.QPushButton('Apply')
        self.applyBtn.pressed.connect(self.applyWeights)

        self.buttonLayout.addWidget(self.extractButton)
        self.buttonLayout.addWidget(self.applyBtn)

        self.centralWidget().layout().addLayout(self.buttonLayout)

    @classmethod
    def createTableWidgetItem(cls, text, height=16):
        """
        Method used to create a table widget item from the supplied text value.

        :type text: str
        :type height: int
        :rtype: QtGui.QStandardItem
        """

        # Create item and resize based on text width
        #
        item = QtWidgets.QTableWidgetItem(text)
        textWidth = cls.getTextWidth(item, text)

        item.setSizeHint(QtCore.QSize(textWidth, height))
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return item

    @classmethod
    def createListWidgetItem(cls, text, height=16):
        """
        Convenience function for quickly creating QStandardItems.

        :type text: str
        :type height: int
        :rtype: QtGui.QStandardItem
        """

        # Create item and resize based on text width
        #
        item = QtWidgets.QListWidgetItem(text)
        textWidth = cls.getTextWidth(item, text)

        item.setSizeHint(QtCore.QSize(textWidth, height))
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return item

    @property
    def clipboard(self):
        """
        Getter method used to retrieve the clipboard items.

        :rtype: list[ClipboardItem]
        """

        return self._clipboard

    def selectedMethod(self):
        """
        Method used to retrieve the selected remapping algorithm.

        :rtype: int
        """

        return self.methodComboBox.currentIndex()

    def selectedRow(self):
        """
        Method used to retrieve the selected row index.

        :rtype: int
        """

        return self.clipboardTableWidget.selectionModel().currentIndex().row()

    def addRow(self, skin):
        """
        Creates a new row based on the supplied skin cluster object.

        :type skin: fnskin.FnSkin
        :rtype: None
        """

        # Check value type
        #
        if not skin.isValid():

            raise TypeError('addRow() expects a valid skin!')

        # Get active selection
        #
        vertexIndices = skin.selection()
        numVertexIndices = len(vertexIndices)

        if numVertexIndices == 0:

            vertexIndices = skin.vertices()

        # Define clipboard item
        #
        clipboardItem = ClipboardItem(skin=skin, selection=vertexIndices)
        self._clipboard.append(clipboardItem)

        # Create standard items
        #
        item1 = self.createTableWidgetItem('%s' % skin.name())
        item2 = self.createTableWidgetItem('%s' % len(vertexIndices))
        item3 = self.createTableWidgetItem('%s' % strftime("%Y-%m-%d %H:%M:%S", gmtime()))

        # Create trash button
        #
        item4 = QtWidgets.QPushButton()
        item4.setIcon(iconutils.getIconByName('delete'))
        item4.clicked.connect(self.trash)

        # Parent items to cells
        #
        rowIndex = self.clipboardTableWidget.rowCount()
        self.clipboardTableWidget.insertRow(rowIndex)

        self.clipboardTableWidget.setItem(rowIndex, 0, item1)
        self.clipboardTableWidget.setItem(rowIndex, 1, item2)
        self.clipboardTableWidget.setItem(rowIndex, 2, item3)
        self.clipboardTableWidget.setCellWidget(rowIndex, 3, item4)

        # Resize columns
        #
        self.clipboardTableWidget.resizeColumnToContents(0)
        self.clipboardTableWidget.resizeColumnToContents(1)

        # Select new row
        #
        self.clipboardTableWidget.selectRow(rowIndex)

    def invalidate(self):
        """
        Invalidates the user interface.
        This consists of repopulating the influence list.

        :rtype: bool
        """

        # Clear all existing rows
        #
        self.influenceListWidget.clear()

        # Get selected clipboard item
        #
        selectedRow = self.selectedRow()

        if selectedRow is None:

            return

        clipboardItem = self._clipboard[selectedRow]
        skin = clipboardItem.skin

        # Collect used influences
        #
        influences = skin.influences()
        usedInfluenceIds = skin.getUsedInfluenceIds(*clipboardItem.selection)

        for influenceId in usedInfluenceIds:

            # Create item from influence name
            #
            influenceName = influences(influenceId).name()

            item = self.createListWidgetItem(influenceName)
            self.influenceListWidget.addItem(item)

        # Set selection to first item
        #
        self.influenceListWidget.setCurrentRow(0)

    def selectionChanged(self, selected, deselected):
        """
        Trigger method used to update the influences list.

        :type selected: QtCore.QItemSelection
        :type deselected: QtCore.QItemSelection
        :rtype: None
        """

        self.invalidate()

    def trash(self):
        """
        Slot method called whenever the user clicks the trash button.

        :rtype: None
        """

        # Get index associated with sender
        #
        sender = self.sender()
        removeAt = self.clipboardTableWidget.indexAt(sender.pos()).row()

        # Remove row from table
        #
        self.clipboardTableWidget.removeRow(removeAt)

        # Remove item from clipboard
        #
        del self._clipboard[removeAt]

    def extractWeights(self):
        """
        Commits the selected mesh to the clipboard.

        :rtype: None
        """

        # Get active selection
        #
        fnSkin = fnskin.FnSkin()
        selection = fnskin.FnSkin.getActiveSelection()

        for obj in selection:

            # Try and initialize function set
            #
            success = fnSkin.trySetObject(obj)

            if not success:

                continue

            # Append row using skin
            #
            self.addRow(fnSkin)

    def applyWeights(self):
        """
        Method used to apply the selected clipboard item to the active selection.

        :rtype: bool
        """

        # Get active selection
        #
        selection = fnskin.FnSkin.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount != 1:

            log.warning('Unable to apply weights to active selection!')
            return

        # Try and initialize function set
        #
        otherSkin = fnskin.FnSkin()
        success = otherSkin.trySetObject(selection[0])

        if not success:

            return

        # Get selected row
        #
        selectedRow = self.selectedRow()
        selectedMethod = self.selectedMethod()

        if selectedRow is None or selectedMethod is None:

            log.warning('Unable to apply weights using selected row!')
            return

        # Initialize transfer object
        #
        clipboardItem = self._clipboard[selectedRow]
        Transfer = self._methods[selectedMethod]

        instance = Transfer(clipboardItem.skin.object(), clipboardItem.selection)
        return instance.transfer(otherSkin, otherSkin.selection())
