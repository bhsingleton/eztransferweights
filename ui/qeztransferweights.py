from Qt import QtCore, QtWidgets, QtGui
from collections import namedtuple
from dcc import fnscene, fnnode, fnskin
from dcc.ui import quicwindow
from ..libs import closestpoint, inversedistance, pointonsurface, skinwrap

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'selection'))


class QEzTransferWeights(quicwindow.QUicWindow):
    """
    Overload of QUicWindow used for transferring skin weights between different meshes.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :key parent: QtWidgets.QWidget
        :key flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QEzTransferWeights, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._scene = fnscene.FnScene()
        self._clipboard = []
        self._methods = [
            closestpoint.ClosestPoint,
            inversedistance.InverseDistance,
            pointonsurface.PointOnSurface,
            skinwrap.SkinWrap
        ]
    # endregion

    # region Properties
    @property
    def scene(self):
        """
        Getter method that returns the scene function set.

        :rtype: fnscene.FnScene
        """

        return self._scene

    @property
    def clipboard(self):
        """
        Getter method that returns the clipboard items.

        :rtype: List[ClipboardItem]
        """

        return self._clipboard
    # endregion

    # region Methods
    def postLoad(self, *args, **kwargs):
        """
        Called after the user interface has been loaded.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzTransferWeights, self).postLoad(*args, **kwargs)

        # Initialize clipboard widget
        #
        horizontalHeader = self.clipboardTableWidget.horizontalHeader()  # type: QtWidgets.QHeaderView
        horizontalHeader.setStretchLastSection(False)
        horizontalHeader.resizeSection(2, 24)
        horizontalHeader.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        horizontalHeader.resizeSection(1, 100)
        horizontalHeader.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        horizontalHeader.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        verticalHeader = self.clipboardTableWidget.verticalHeader()  # type: QtWidgets.QHeaderView
        verticalHeader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        verticalHeader.setDefaultSectionSize(24)

    def createTableWidgetItem(self, text):
        """
        Method used to create a table widget item from the supplied text value.

        :type text: str
        :rtype: QtGui.QStandardItem
        """

        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return item

    def createListWidgetItem(self, text):
        """
        Convenience function for quickly creating QStandardItems.

        :type text: str
        :rtype: QtGui.QStandardItem
        """

        item = QtWidgets.QListWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return item

    def clipboardCount(self):
        """
        Evaluates the number of clipboard items.

        :rtype: int
        """

        return len(self._clipboard)

    def currentClipboardItem(self):
        """
        Returns the current clipboard item.

        :rtype: ClipboardItem
        """

        row = self.currentRow()
        clipboardCount = self.clipboardCount()

        if 0 <= row < clipboardCount:

            return self.clipboard[row]

        else:

            return None

    def currentMethod(self):
        """
        Method used to retrieve the selected remapping algorithm.

        :rtype: int
        """

        return self.methodComboBox.currentIndex()

    def currentRow(self):
        """
        Method used to retrieve the selected row index.

        :rtype: int
        """

        return self.clipboardTableWidget.selectionModel().currentIndex().row()

    def selectRow(self, row):
        """
        Selects the specified row from the clipboard table.

        :type row: int
        :rtype: None
        """

        rowCount = self.clipboardTableWidget.rowCount()

        if 0 <= row < rowCount:

            self.clipboardTableWidget.selectRow(row)

    def addRow(self, skin):
        """
        Creates a new row based on the supplied skin cluster object.

        :type skin: fnskin.FnSkin
        :rtype: None
        """

        # Check if skin is valid
        #
        if not skin.isValid():

            raise TypeError('addRow() expects a valid skin deformer!')

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
        fnShape = fnnode.FnNode(skin.shape())

        item1 = self.createTableWidgetItem(fnShape.name())
        item2 = self.createTableWidgetItem(str(len(vertexIndices)))

        item3 = QtWidgets.QPushButton(QtGui.QIcon(':dcc/icons/delete.svg'), '')
        item3.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        item3.clicked.connect(self.on_deletePushButton_clicked)

        # Parent items to cells
        #
        rowIndex = self.clipboardTableWidget.rowCount()
        self.clipboardTableWidget.insertRow(rowIndex)
        self.clipboardTableWidget.setItem(rowIndex, 0, item1)
        self.clipboardTableWidget.setItem(rowIndex, 1, item2)
        self.clipboardTableWidget.setCellWidget(rowIndex, 2, item3)

        # Resize columns and select row
        #
        self.clipboardTableWidget.selectRow(rowIndex)

    def removeRow(self, row):
        """
        Removes the specified row from the table widget.

        :type row: int
        :rtype: None
        """

        # Remove clipboard item
        #
        self.clipboardTableWidget.clearSelection()
        self.clipboardTableWidget.removeRow(row)

        del self._clipboard[row]

        # Select next available clipboard item
        #
        self.selectRow(row - 1)

    def invalidate(self):
        """
        Resets the influence list widget with the current clipboard item's used influences.

        :rtype: None
        """

        # Clear all existing rows
        #
        self.influenceListWidget.clear()

        # Get current clipboard item
        #
        clipboardItem = self.currentClipboardItem()

        if clipboardItem is None:

            return

        # Collect used influences
        #
        skin = clipboardItem.skin

        influences = skin.influences()
        usedInfluenceIds = skin.getUsedInfluenceIds(*clipboardItem.selection)

        for influenceId in usedInfluenceIds:

            # Create item from influence name
            #
            influenceName = influences[influenceId].name()

            item = self.createListWidgetItem(influenceName)
            self.influenceListWidget.addItem(item)

        # Set selection to first item
        #
        self.influenceListWidget.setCurrentRow(0)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_deletePushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for deleting the associated row.

        :type checked: bool
        :rtype: None
        """

        # Get index associated with sender
        #
        sender = self.sender()
        removeAt = self.clipboardTableWidget.indexAt(sender.pos()).row()

        # Remove clipboard item
        #
        self.removeRow(removeAt)

    @QtCore.Slot()
    def on_clipboardTableWidget_itemSelectionChanged(self):
        """
        Item selection changed slot method responsible for invalidating the influence list.

        :rtype: None
        """

        self.invalidate()

    @QtCore.Slot(bool)
    def on_createPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for creating a skin deformer from the current influences.

        :type checked: bool
        :rtype: None
        """

        log.info('Coming soon!')

    @QtCore.Slot(bool)
    def on_extractPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for extracting skin weights from the active selection.

        :type checked: bool
        :rtype: None
        """

        # Add active selection
        #
        selection = self.scene.getActiveSelection()
        skin = fnskin.FnSkin()

        for obj in selection:

            success = skin.trySetObject(obj)

            if success:

                self.addRow(skin)

            else:

                continue

    @QtCore.Slot(bool)
    def on_transferPushButton_clicked(self, checked=False):
        """
        Clicked slot method responsible for applying the selected weights to the active selection.

        :type checked: bool
        :rtype: None
        """

        # Get active selection
        #
        selection = self.scene.getActiveSelection()
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
        clipboardItem = self.currentClipboardItem()

        if clipboardItem is None:

            log.warning('Unable to apply weights using selected row!')
            return

        # Initialize transfer object
        #
        currentMethod = self.currentMethod()
        cls = self._methods[currentMethod]

        instance = cls(clipboardItem.skin, clipboardItem.selection)
        return instance.transfer(otherSkin, otherSkin.selection())
    # endregion
