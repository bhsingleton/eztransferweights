from Qt import QtCore, QtWidgets, QtGui
from collections import namedtuple
from dcc import fnscene, fnnode, fnmesh, fnskin
from dcc.ui import quicwindow
from ..libs import closestpoint, inversedistance, pointonsurface, skinwrap

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'influences', 'selection'))


class QEzTransferWeights(quicwindow.QUicWindow):
    """
    Overload of `QUicWindow` that transfers skin weights between different meshes.
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
        self._faceLimit = 3
        self._distanceInfluence = 1.2
        self._falloff = 0
        self._clipboard = []
        self._methods = [
            closestpoint.ClosestPoint,
            inversedistance.InverseDistance,
            pointonsurface.PointOnSurface,
            skinwrap.SkinWrap
        ]

        # Declare public variables
        #
        self.mainWidget = None
        self.mainSplitter = None

        self.clipboardGroupBox = None
        self.clipboardTableWidget = None
        self.methodWidget = None
        self.methodLabel = None
        self.methodComboBox = None
        self.settingsToolButton = None
        self.settingsMenu = None
        self.faceLimitAction = None
        self.distanceInfluenceAction = None
        self.falloffAction = None

        self.influenceGroupBox = None
        self.influenceListWidget = None
        self.createPushButton = None

        self.buttonsWidget = None
        self.extractPushButton = None
        self.transferPushButton = None

        self.progressBar = None
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

        # Initialize settings menu
        #
        self.settingsMenu = QtWidgets.QMenu(parent=self.settingsToolButton)
        self.settingsMenu.setObjectName('settingsMenu')

        self.faceLimitAction = QtWidgets.QAction('Set Face Limit', parent=self.settingsMenu)
        self.faceLimitAction.setObjectName('faceLimitAction')
        self.faceLimitAction.triggered.connect(self.on_faceLimitAction_triggered)

        self.distanceInfluenceAction = QtWidgets.QAction('Set Distance Multiplier', parent=self.settingsMenu)
        self.distanceInfluenceAction.setObjectName('distanceInfluenceAction')
        self.distanceInfluenceAction.triggered.connect(self.on_distanceInfluenceAction_triggered)

        self.falloffAction = QtWidgets.QAction('Set Falloff', parent=self.settingsMenu)
        self.falloffAction.setObjectName('falloffAction')
        self.falloffAction.triggered.connect(self.on_falloffAction_triggered)

        self.settingsMenu.addActions([self.faceLimitAction, self.distanceInfluenceAction, self.falloffAction])

        self.settingsToolButton.setMenu(self.settingsMenu)

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

        :rtype: Union[ClipboardItem, None]
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

        # Get used influence names
        #
        influences = skin.influences()
        usedInfluenceIds = skin.getUsedInfluenceIds(*vertexIndices)

        usedInfluences = {influenceId: influences[influenceId].absoluteName() for influenceId in usedInfluenceIds}

        # Define clipboard item
        #
        clipboardItem = ClipboardItem(skin=skin, selection=vertexIndices, influences=usedInfluences)
        self._clipboard.append(clipboardItem)

        # Create standard items
        #
        shape = fnnode.FnNode(skin.shape())

        item1 = self.createTableWidgetItem(shape.name())
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

        # Get current clipboard item
        #
        clipboardItem = self.currentClipboardItem()
        self.influenceListWidget.clear()

        if clipboardItem is None:

            return

        # Check if clipboard item is still valid
        #
        if not clipboardItem.skin.isValid():

            return

        # Collect used influences
        #
        for (influenceId, influenceName) in clipboardItem.influences.items():

            # Create item from influence name
            #
            item = self.createListWidgetItem(influenceName)
            self.influenceListWidget.addItem(item)

        # Set selection to first item
        #
        self.influenceListWidget.setCurrentRow(0)

    def updateProgressBar(self, progress):

        self.progressBar.setValue(progress)
    # endregion

    # region Slots
    @QtCore.Slot(bool)
    def on_faceLimitAction_triggered(self, checked=False):
        """
        Slot method for the `faceLimitAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        faceLimit, success = QtWidgets.QInputDialog.getInt(
            self,
            'Set Face Limit',
            'Enter face limit:',
            value=self._faceLimit,
            minValue=0,
            maxValue=30,
            step=1
        )

        if success:

            self._faceLimit = faceLimit

    @QtCore.Slot(bool)
    def on_distanceInfluenceAction_triggered(self, checked=False):
        """
        Slot method for the `distanceInfluenceAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        distanceInfluence, success = QtWidgets.QInputDialog.getDouble(
            self,
            'Set Distance Multiplier',
            'Enter distance multiplier:',
            self._distanceInfluence,
            minValue=0.001,
            maxValue=10.0,
            step=0.1
        )

        if success:

            self._distanceInfluence = distanceInfluence

    @QtCore.Slot(bool)
    def on_falloffAction_triggered(self, checked=False):
        """
        Slot method for the `falloffAction` widget's `triggered` signal.

        :type checked: bool
        :rtype: None
        """

        falloff, success = QtWidgets.QInputDialog.getDouble(
            self,
            'Set Falloff',
            'Enter falloff:',
            self._falloff,
            minValue=0.0,
            maxValue=10.0,
            step=0.1
        )

        if success:

            self._falloff = falloff

    @QtCore.Slot(bool)
    def on_deletePushButton_clicked(self, checked=False):
        """
        Slot method for the `deletePushButton` widget's `clicked` signal.

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
        Slot method for the `clipboardTableWidget` widget's `itemSelectionChanged` signal.

        :rtype: None
        """

        self.invalidate()

    @QtCore.Slot(bool)
    def on_createPushButton_clicked(self, checked=False):
        """
        Slot method for the `createPushButton` widget's `clicked` signal.

        :type checked: bool
        :rtype: None
        """

        # Evaluate active selection
        #
        selection = self.scene.getActiveSelection()
        selectionCount = len(selection)

        if selectionCount == 0:

            log.warning('Invalid selection!')
            return

        # Get selected clipboard item
        #
        clipboardItem = self.currentClipboardItem()

        if clipboardItem is None:

            log.warning('Invalid clipboard selection!')
            return

        # Check if mesh is already skinned
        #
        mesh = selection[0]

        skin = fnskin.FnSkin()
        success = skin.trySetObject(mesh)

        if success:

            log.warning('Selected mesh already has a skin!')
            return

        # Create new skin and add influences
        #
        skin = fnskin.FnSkin.create(mesh)
        skin.setMaxInfluences(clipboardItem.skin.maxInfluences())

        influences = list(clipboardItem.influences.values())
        skin.addInfluence(*influences)

        # Transfer weights to new skin
        #
        instance = closestpoint.ClosestPoint(clipboardItem.skin, clipboardItem.selection)
        instance.transfer(skin, skin.vertices())

    @QtCore.Slot(bool)
    def on_extractPushButton_clicked(self, checked=False):
        """
        Slot method for the `extractPushButton` widget's `clicked` signal.

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
        Slot method for the `transferPushButton` widget's `clicked` signal.

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

            log.warning('Invalid clipboard selection!')
            return

        # Initialize transfer interface
        #
        currentMethod = self.currentMethod()
        cls = self._methods[currentMethod]

        instance = cls(
            clipboardItem.skin,
            clipboardItem.selection,
            faceLimit=self._faceLimit,
            distanceInfluence=self._distanceInfluence,
            falloff=self._falloff
        )

        # Execute transfer
        #
        otherSelection = otherSkin.selection()
        otherSelectionCount = len(otherSelection)
        self.progressBar.setMaximum(otherSelectionCount)

        instance.transfer(otherSkin, otherSkin.selection(), notify=self.updateProgressBar)
    # endregion
