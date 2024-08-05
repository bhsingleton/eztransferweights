import math

from itertools import chain
from scipy.spatial import cKDTree
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
    def transfer(self, otherSkin, vertexIndices, notify=None):
        """
        Transfers the weights from this skin to the other skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :type notify: Union[Callable, None]
        :rtype: None
        """

        # Get the closest points from the point tree
        #
        vertexPoints = otherSkin.controlPoints(*vertexIndices)
        progressFactor = 100.0 / float(len(vertexIndices))

        updates = {}

        for (i, (vertexIndex, vertexPoint)) in enumerate(zip(vertexIndices, vertexPoints), start=1):

            # Calculate closest vertex
            #
            closestDistances, closestIndices = self.pointTree.query([vertexPoint])
            closestIndex = self.localVertexMap[closestIndices[0]]
            closestWeights = self.skin.vertexWeights(closestIndex)

            updates[vertexIndex] = closestWeights[closestIndex]

            # Signal progress update
            #
            if callable(notify):

                progress = int(math.ceil(float(i) * progressFactor))
                notify(progress)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via closest point!')
    # endregion
