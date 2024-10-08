import math

from itertools import chain
from . import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class PointOnSurface(abstracttransfer.AbstractTransfer):
    """
    Overload of `AbstractTransfer` that transfers weights by closest point on surface.
    """

    # region Dunderscores
    __slots__ = ('_faceIndices',)
    __title__ = 'Point on Surface'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :rtype: None
        """

        # Call parent method
        #
        super(PointOnSurface, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._faceIndices = set(self.mesh.iterConnectedFaces(*self.vertexIndices, componentType=self.mesh.ComponentType.Vertex))
    # endregion

    # region Properties
    @property
    def faceIndices(self):
        """
        Getter method that returns the cached face indices.

        :rtype: List[int]
        """

        return self._faceIndices
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

        # Assign mesh to function set
        #
        points = otherSkin.controlPoints(*vertexIndices)
        hits = self.mesh.closestPointOnSurface(*points, dataset=self.faceIndices)
        progressFactor = 100.0 / float(len(vertexIndices))

        updates = {}

        for (i, (vertexIndex, hit)) in enumerate(zip(vertexIndices, hits), start=1):

            # Get associated skin weights
            #
            faceVertexIndices = hit.faceVertexIndices
            vertexWeights = self.skin.vertexWeights(*faceVertexIndices)

            # Evaluate face topology
            #
            numFaceVertexIndices = len(faceVertexIndices)

            if numFaceVertexIndices == 3:

                # Calculate barycentric weights
                #
                updates[vertexIndex] = self.skin.barycentricWeights(faceVertexIndices, hit.baryCoords)

            elif numFaceVertexIndices == 4:

                # Calculate bilinear weights
                #
                updates[vertexIndex] = self.skin.bilinearWeights(faceVertexIndices, hit.biCoords)

            else:

                # Calculate inverse distance weights
                #
                distances = [hit.point.distanceBetween(otherPoint) for otherPoint in hit.faceVertexPoints]
                average = self.skin.inverseDistanceWeights(vertexWeights, distances)

                updates[vertexIndex] = average

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

        log.info('Finished transferring weights via point on surface!')
    # endregion
