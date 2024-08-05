from Qt import QtCore, QtWidgets, QtGui
from collections import namedtuple
from dcc import fnscene, fnnode, fnmesh, fnskin
from dcc.ui import qsingletonwindow
from ..libs import closestpoint, inversedistance, pointonsurface, skinwrap

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


ClipboardItem = namedtuple('ClipboardItem', ('skin', 'influences', 'selection'))


class QEzTransferWeights(qsingletonwindow.QSingletonWindow):
    """
    Overload of `QSingletonWindow` that transfers skin weights between different meshes.
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

    def __setup_ui__(self, *args, **kwargs):
        """
        Private method that initializes the user interface.

        :rtype: None
        """

        # Call parent method
        #
        super(QEzTransferWeights, self).__setup_ui__(self, *args, **kwargs)

        # Initialize main window
        #
        self.setWindowTitle("|| Ez'Transfer-Weights")
        self.setMinimumSize(QtCore.QSize(600, 300))

        # Initialize central widget
        #
        centralLayout = QtWidgets.QVBoxLayout()
        centralLayout.setObjectName('centralLayout')

        centralWidget = QtWidgets.QWidget()
        centralWidget.setObjectName('centralWidget')
        centralWidget.setLayout(centralLayout)

        self.setCentralWidget(centralWidget)

        # Initialize transfer method widget
        #
        self.methodLayout = QtWidgets.QHBoxLayout()
        self.methodLayout.setObjectName('methodLayout')
        self.methodLayout.setContentsMargins(0, 0, 0, 0)

        self.methodWidget = QtWidgets.QWidget()
        self.methodWidget.setObjectName('methodWidget')
        self.methodWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.methodWidget.setFixedHeight(24)
        self.methodWidget.setLayout(self.methodLayout)

        self.methodLabel = QtWidgets.QLabel('Method:')
        self.methodLabel.setObjectName('methodLabel')
        self.methodLabel.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred))
        self.methodLabel.setFixedWidth(50)
        self.methodLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.methodComboBox = QtWidgets.QComboBox()
        self.methodComboBox.setObjectName('methodLabel')
        self.methodComboBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.methodComboBox.addItems(['Closest Point', 'Inverse Distance', 'Point on Surface', 'Skin Wrap', 'Robust Inpaint'])

        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)

        self.settingsToolButton = QtWidgets.QToolButton()
        self.settingsToolButton.setObjectName('settingsToolButton')
        self.settingsToolButton.setSizePolicy(sizePolicy)
        self.settingsToolButton.setIcon(QtGui.QIcon(':/dcc/icons/settings.svg'))
        self.settingsToolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        self.methodLayout.addWidget(self.methodLabel)
        self.methodLayout.addWidget(self.methodComboBox)
        self.methodLayout.addWidget(self.settingsToolButton)

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

        # Initialize clipboard widget
        #
        self.clipboardLayout = QtWidgets.QVBoxLayout()
        self.clipboardLayout.setObjectName('clipboardLayout')
        self.clipboardLayout.setContentsMargins(0, 0, 0, 0)

        self.clipboardWidget = QtWidgets.QWidget()
        self.clipboardWidget.setObjectName('clipboardWidget')
        self.clipboardWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.clipboardWidget.setLayout(self.clipboardLayout)

        self.clipboardHeader = QtWidgets.QGroupBox('Clipboard')
        self.clipboardHeader.setObjectName('clipboardHeader')
        self.clipboardHeader.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.clipboardHeader.setAlignment(QtCore.Qt.AlignCenter)
        self.clipboardHeader.setFlat(True)

        self.clipboardTableWidget = QtWidgets.QTableWidget()
        self.clipboardTableWidget.setObjectName('clipboardTableWidget')
        self.clipboardTableWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.clipboardTableWidget.setStyleSheet('QTableWidget::item { height: 24px; }')
        self.clipboardTableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.clipboardTableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.clipboardTableWidget.setAlternatingRowColors(True)
        self.clipboardTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.clipboardTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.clipboardTableWidget.itemSelectionChanged.connect(self.on_clipboardTableWidget_itemSelectionChanged)

        self.clipboardTableWidget.setColumnCount(3)
        self.clipboardTableWidget.setHorizontalHeaderLabels(['Name', 'Points', ''])
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

        self.clipboardFooter = QtWidgets.QFrame()
        self.clipboardFooter.setObjectName('clipboardFooter')
        self.clipboardFooter.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.clipboardFooter.setFrameShape(QtWidgets.QFrame.HLine)
        self.clipboardFooter.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.clipboardLayout.addWidget(self.clipboardHeader)
        self.clipboardLayout.addWidget(self.clipboardTableWidget)
        self.clipboardLayout.addWidget(self.methodWidget)
        self.clipboardLayout.addWidget(self.clipboardFooter)

        # Initialize influence widget
        #
        self.influenceLayout = QtWidgets.QVBoxLayout()
        self.influenceLayout.setObjectName('influenceLayout')
        self.influenceLayout.setContentsMargins(0, 0, 0, 0)

        self.influenceWidget = QtWidgets.QWidget()
        self.influenceWidget.setObjectName('influenceWidget')
        self.influenceWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.influenceWidget.setLayout(self.influenceLayout)

        self.influenceHeader = QtWidgets.QGroupBox('Influences')
        self.influenceHeader.setObjectName('influenceHeader')
        self.influenceHeader.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.influenceHeader.setAlignment(QtCore.Qt.AlignCenter)
        self.influenceHeader.setFlat(True)

        self.influenceListWidget = QtWidgets.QListWidget()
        self.influenceListWidget.setObjectName('influenceListWidget')
        self.influenceListWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred))
        self.influenceListWidget.setStyleSheet('QListWidget::item { height: 24px; }')
        self.influenceListWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.influenceListWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.influenceListWidget.setAlternatingRowColors(True)
        self.influenceListWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.influenceListWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.influenceListWidget.setViewMode(QtWidgets.QListWidget.ListMode)
        self.influenceListWidget.setUniformItemSizes(True)
        self.influenceListWidget.setItemAlignment(QtCore.Qt.AlignCenter)

        self.createPushButton = QtWidgets.QPushButton('Create Skin')
        self.createPushButton.setObjectName('createPushButton')
        self.createPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.createPushButton.setFixedHeight(24)
        self.createPushButton.clicked.connect(self.on_createPushButton_clicked)

        self.influenceFooter = QtWidgets.QFrame()
        self.influenceFooter.setObjectName('influenceFooter')
        self.influenceFooter.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed))
        self.influenceFooter.setFrameShape(QtWidgets.QFrame.HLine)
        self.influenceFooter.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.influenceLayout.addWidget(self.influenceHeader)
        self.influenceLayout.addWidget(self.influenceListWidget)
        self.influenceLayout.addWidget(self.createPushButton)
        self.influenceLayout.addWidget(self.influenceFooter)

        # Initialize splitter widget
        #
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.setObjectName('splitter')
        self.splitter.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        self.splitter.addWidget(self.clipboardWidget)
        self.splitter.addWidget(self.influenceWidget)

        centralLayout.addWidget(self.splitter)

        # Initialize interop widget
        #
        self.interopLayout = QtWidgets.QHBoxLayout()
        self.interopLayout.setObjectName('interopLayout')
        self.interopLayout.setContentsMargins(0, 0, 0, 0)

        self.interopWidget = QtWidgets.QWidget()
        self.interopWidget.setObjectName('interopWidget')
        self.interopWidget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.interopWidget.setFixedHeight(24)
        self.interopWidget.setLayout(self.interopLayout)

        self.extractPushButton = QtWidgets.QPushButton('Extract Weights')
        self.extractPushButton.setObjectName('extractPushButton')
        self.extractPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.extractPushButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.extractPushButton.clicked.connect(self.on_extractPushButton_clicked)

        self.transferPushButton = QtWidgets.QPushButton('Transfer Weights')
        self.transferPushButton.setObjectName('transferPushButton')
        self.transferPushButton.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred))
        self.transferPushButton.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.transferPushButton.clicked.connect(self.on_transferPushButton_clicked)

        self.interopLayout.addWidget(self.extractPushButton)
        self.interopLayout.addWidget(self.transferPushButton)

        centralLayout.addWidget(self.interopWidget)

        # Initialize progress bar
        #
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setObjectName('progressBar')
        self.progressBar.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed))
        self.progressBar.setFixedHeight(24)
        self.progressBar.setTextVisible(True)
        self.progressBar.setValue(0.0)

        centralLayout.addWidget(self.progressBar)
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
    def createTableWidgetItem(self, text):
        """
        Returns a new table widget item with the specified text.
        By default, the text alignment is centered!

        :type text: str
        :rtype: QtWidgets.QTableWidgetItem
        """

        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

        return item

    def createListWidgetItem(self, text):
        """
        Returns a new list widget item with the specified text.
        By default, the text alignment is centered!

        :type text: str
        :rtype: QListWidgetItem
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
        Returns the selected transfer method.

        :rtype: int
        """

        return self.methodComboBox.currentIndex()

    def currentRow(self):
        """
        Returns the selected row index.

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
        instance.transfer(otherSkin, otherSkin.selection(), notify=self.updateProgressBar)
    # endregion
