import math

from itertools import chain
from eztransferweights.abstract import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class InverseDistance(abstracttransfer.AbstractTransfer):
    """
    Overload of TransferWeights used to turn geometry into a point cloud.
    This data is then used for inverse distance transfer.
    """

    __slots__ = ('points',)

    def __init__(self, *args, **kwargs):
        """
        Overloaded method called after a new instance has been created.
        """

        # Call parent method
        #
        super(InverseDistance, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self.points = self.skin.controlPoints()

    @staticmethod
    def distanceBetween(point, otherPoint):
        """
        Evaluates the distance between two points.

        :type point: list[float, float, float]
        :type otherPoint: list[float, float, float]
        :rtype: float
        """

        return math.sqrt(math.pow(otherPoint[0] - point[0], 2.0) + math.pow(otherPoint[1] - point[1], 2.0) + math.pow(otherPoint[2] - point[2], 2.0))

    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: list[int]
        :rtype: None
        """

        # Collect inverse distance weights
        #
        points = otherSkin.controlPoints()
        updates = {}

        for vertexIndex in vertexIndices:

            point = points[vertexIndex]

            vertices = self.skin.vertexWeights(*self.vertexIndices)
            distances = [self.distanceBetween(point, self.points[x]) for x in self.vertexIndices]

            updates[vertexIndex] = self.skin.inverseDistanceWeights(vertices, distances)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via inverse distance!')
