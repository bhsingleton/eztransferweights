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
    __slots__ = ('_vertexPoints', '_power')
    __title__ = 'Inverse Distance'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :key power: float
        :rtype: None
        """

        # Call parent method
        #
        super(InverseDistance, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._vertexPoints = self.skin.controlPoints(*self.vertexIndices)
        self._power = kwargs.get('power', 2.0)
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
    def power(self):
        """
        Getter method that returns the distance power.

        :rtype: float
        """

        return self._power
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

        # Collect inverse distance weights
        #
        vertexPoints = otherSkin.controlPoints(*vertexIndices)
        vertexWeights = self.skin.vertexWeights(*self.vertexIndices)

        updates = {}

        for (progress, (vertexIndex, vertexPoint)) in enumerate(zip(vertexIndices, vertexPoints), start=1):

            # Calculate inverse distance
            #
            distances = [vertexPoint.distanceBetween(otherPoint) for otherPoint in self.vertexPoints]
            average = self.skin.inverseDistanceWeights(vertexWeights, distances, power=self.power)

            updates[vertexIndex] = average

            # Signal progress update
            #
            if callable(notify):

                notify(progress)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via inverse distance!')
    # endregion
