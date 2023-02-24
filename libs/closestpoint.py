from scipy.spatial import cKDTree
from itertools import chain
from . import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ClosestPoint(abstracttransfer.AbstractTransfer):
    """
    Overload of `AbstractTransfer` that transfers weights by closest point.
    """

    # region Dunderscores
    __slots__ = ('_vertexPoints', '_pointTree')
    __title__ = 'Closest Point'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :rtype: None
        """

        # Call parent method
        #
        super(ClosestPoint, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._vertexPoints = self.skin.controlPoints(*self.vertexIndices)
        self._pointTree = cKDTree(self._vertexPoints)
    # endregion

    # region Properties
    @property
    def vertexPoints(self):
        """
        Getter method that returns the vertex points.

        :rtype: List[vector.Vector]
        """

        return self._vertexPoints

    @property
    def pointTree(self):
        """
        Getter method that returns the point tree.

        :rtype: cKDTree
        """

        return self._pointTree
    # endregion

    # region Methods
    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this skin to the other skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :rtype: None
        """

        # Get the closest points from the point tree
        #
        points = otherSkin.controlPoints(*vertexIndices)
        distances, closestIndices = self.pointTree.query(points)

        # Get associated vertex weights
        # Remember we have to convert our local indices back to global!
        #
        closestVertexIndices = [self.vertexMap[x] for x in closestIndices]
        closestVertices = self.skin.vertexWeights(*closestVertexIndices)

        updates = {vertexIndex: closestVertices[closestVertexIndex] for (vertexIndex, closestVertexIndex) in zip(vertexIndices, closestVertexIndices)}

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via closest point!')
    # endregion
