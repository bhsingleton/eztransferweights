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
    Abstract class used to outline transfer algorithms.
    """

    __slots__ = ('_skin', '_mesh', '_vertexIndices')

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.
        """

        # Call parent method
        #
        super(AbstractTransfer, self).__init__()

        # Declare private variables
        #
        self._skin = fnskin.FnSkin()
        self._mesh = fnmesh.FnMesh()
        self._vertexIndices = []

        # Inspect arguments
        #
        numArgs = len(args)

        if numArgs == 1:

            # Try and initialize function set
            #
            skin = args[0]
            success = self._skin.trySetObject(skin)

            if not success:

                raise TypeError('%s() expects a valid skin!' % self.className)

            # Assign complete list of vertices
            #
            self._mesh.setObject(self._skin.intermediateObject())
            self._vertexIndices = range(self._skin.numControlPoints())

        elif numArgs == 2:

            # Try and initialize function set
            #
            skin = args[0]
            success = self._skin.trySetObject(skin)

            if not success:

                raise TypeError('%s() expects a valid skin!' % self.className)

            # Check vertex elements type
            #
            vertexIndices = args[1]

            if not isinstance(vertexIndices, (list, tuple, set)):

                raise TypeError('%s() expects a list (%s given)!' % (self.className, type(vertexIndices).__name__))

            # Store vertex elements
            #
            self._mesh.setObject(self._skin.intermediateObject())
            self._vertexIndices = vertexIndices

        else:

            raise TypeError('TransferWeights() expects 1 or 2 arguments (%s given)!' % numArgs)

    @classproperty
    def className(cls):
        """
        Getter method that returns the name of this class.

        :rtype: str
        """

        return cls.__name__

    @property
    def mesh(self):
        """
        Getter method that returns the mesh function set.

        :rtype: fnmesh.FnMesh
        """

        return self._mesh

    @property
    def skin(self):
        """
        Getter method that returns the skin function set.

        :rtype: fnskin.FnSkin
        """

        return self._skin

    @property
    def vertexIndices(self):
        """
        Getter method that returns the cached vertex indices.

        :rtype: list[int]
        """

        return self._vertexIndices

    @abstractmethod
    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: list[int]
        :rtype: None
        """

        pass
