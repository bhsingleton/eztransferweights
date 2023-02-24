from itertools import chain
from . import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class InverseDistance(abstracttransfer.AbstractTransfer):
    """
    Overload of `AbstractTransfer` that transfers weights via inverse distance.
    """

    # region Dunderscores
    __slots__ = ('_vertexPoints',)
    __title__ = 'Inverse Distance'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :rtype: None
        """

        # Call parent method
        #
        super(InverseDistance, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._vertexPoints = self.skin.controlPoints()
    # endregion

    # region Properties
    @property
    def vertexPoints(self):
        """
        Getter method that returns the vertex points.

        :rtype: List[vector.Vector]
        """

        return self._vertexPoints
    # endregion

    # region Methods
    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :rtype: None
        """

        # Collect inverse distance weights
        #
        points = otherSkin.controlPoints()
        updates = {}

        for vertexIndex in vertexIndices:

            point = points[vertexIndex]
            vertexWeights = self.skin.vertexWeights(*self.vertexIndices)
            distances = [point.distanceBetween(self.vertexPoints[x]) for x in self.vertexIndices]

            updates[vertexIndex] = self.skin.inverseDistanceWeights(vertexWeights, distances)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via inverse distance!')
    # endregion
