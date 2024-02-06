from abc import ABCMeta, abstractmethod
from six import with_metaclass
from dcc import fnskin, fnmesh
from dcc.decorators.classproperty import classproperty

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class AbstractTransfer(with_metaclass(ABCMeta, object)):
    """
    Abstract base class that outlines weight transfer behavior.
    """

    # region Dunderscores
    __slots__ = ('_mesh', '_skin', '_vertexIndices', '_vertexMap')
    __title__ = ''

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :rtype: None
        """

        # Call parent method
        #
        super(AbstractTransfer, self).__init__()

        # Declare private variables
        #
        self._skin = None
        self._mesh = None
        self._vertexIndices = []
        self._vertexMap = {}

        # Inspect arguments
        #
        numArgs = len(args)

        if numArgs == 1:

            # Inspect skin type
            #
            skin = args[0]

            if not isinstance(skin, fnskin.FnSkin):

                raise TypeError('%s() expects a valid skin (%s given)!' % (self.className, type(skin).__name__))

            # Store all vertex elements
            #
            self._skin = skin
            self._mesh = fnmesh.FnMesh(self.skin.intermediateObject())
            self._vertexIndices = list(range(self.skin.numControlPoints()))
            self._vertexMap = dict(enumerate(self._vertexIndices))

        elif numArgs == 2:

            # Inspect skin type
            #
            skin = args[0]

            if not isinstance(skin, fnskin.FnSkin):

                raise TypeError('%s() expects a valid skin (%s given)!' % (self.className, type(skin).__name__))

            # Inspect vertex elements type
            #
            vertexIndices = args[1]

            if not isinstance(vertexIndices, (list, tuple, set)):

                raise TypeError('%s() expects a valid list (%s given)!' % (self.className, type(vertexIndices).__name__))

            # Store vertex elements
            #
            self._skin = skin
            self._mesh = fnmesh.FnMesh(self._skin.intermediateObject())
            self._vertexIndices = vertexIndices
            self._vertexMap = dict(enumerate(self._vertexIndices))

        else:

            raise TypeError('TransferWeights() expects 1 or 2 arguments (%s given)!' % numArgs)
    # endregion

    # region Properties
    @classproperty
    def className(cls):
        """
        Getter method that returns the name of this class.

        :rtype: str
        """

        return cls.__name__

    @classproperty
    def title(cls):
        """
        Getter method that returns the name of this class.

        :rtype: str
        """

        return cls.__title__

    @property
    def skin(self):
        """
        Getter method that returns the skin function set.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @property
    def mesh(self):
        """
        Getter method that returns the mesh function set.

        :rtype: fnmesh.FnMesh
        """

        return self._mesh

    @property
    def vertexIndices(self):
        """
        Getter method that returns the vertex index dataset.

        :rtype: List[int]
        """

        return self._vertexIndices

    @property
    def vertexMap(self):
        """
        Getter method that returns the vertex local to global map.

        :rtype: Dict[int, int]
        """

        return self._vertexIndices
    # endregion

    # region Methods
    @abstractmethod
    def transfer(self, otherSkin, vertexIndices, notify=None):
        """
        Transfers the weights from this skin to the other skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :type notify: Union[Callable, None]
        :rtype: None
        """

        pass
    # endregion
