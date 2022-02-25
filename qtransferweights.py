from PySide2 import QtCore, QtWidgets, QtGui
from collections import namedtuple
from dcc import fnskin
from dcc.userinterface import quicwindow, qiconlibrary
from transferweights.methods import pointcloud, inversedistance, pointonsurface

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'selection'))


class QTransferWeights(quicwindow.QUicWindow):
    """
    Overload of QProxyWindow used for transferring skin weights between different meshes.
    """

    # region Dunderscores
    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :keyword parent: QtWidgets.QWidget
        :keyword flags: QtCore.Qt.WindowFlags
        :rtype: None
        """

        # Call parent method
        #
        super(QTransferWeights, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._clipboard = []

        self._methods = [
            pointcloud.PointCloud,
            inversedistance.InverseDistance,
            pointonsurface.PointOnSurface
        ]
    # endregion

    # region Properties
    @property
    def clipboard(self):
        """
        Getter method that returns the clipboard items.

        :rtype: list[ClipboardItem]
        """

        return self._clipboard
    # endregion

    # region Methods
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

        # Check if table is empty
        #
        clipboardCount = self.clipboardCount()

        if clipboardCount > 0:

            row = max(min(row, clipboardCount), 0)
            self.clipboardTableWidget.selectRow(row)

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

        # Create delete button
        #
        item3 = QtWidgets.QPushButton()
        item3.setIcon(qiconlibrary.getIconByName('delete'))
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
        self.clipboardTableWidget.resizeColumnToContents(0)
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
            influenceName = influences(influenceId).name()

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
        Slot method called whenever the user clicks the trash button.

        :rtype: None
        """

        # Get index associated with sender
        #
        sender = self.sender()
        removeAt = self.clipboardTableWidget.indexAt(sender.pos()).row()

        # Remove clipboard item
        #
        self.removeRow(removeAt)

    @QtCore.Slot(QtWidgets.QTableWidgetItem)
    def on_clipboardTableWidget_itemClicked(self, item):

        self.invalidate()

    @QtCore.Slot(bool)
    def on_extractPushButton_clicked(self, checked=False):
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

    @QtCore.Slot(bool)
    def on_transferPushButton_clicked(self, checked=False):
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
        clipboardItem = self.currentClipboardItem()

        if clipboardItem is None:

            log.warning('Unable to apply weights using selected row!')
            return

        # Initialize transfer object
        #
        currentMethod = self.currentMethod()
        cls = self._methods[currentMethod]

        instance = cls(clipboardItem.skin.object(), clipboardItem.selection)
        return instance.transfer(otherSkin, otherSkin.selection())
    # endregion
