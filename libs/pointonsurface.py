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
    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :rtype: None
        """

        # Assign mesh to function set
        #
        points = otherSkin.controlPoints(*vertexIndices)
        hits = self.mesh.closestPointOnSurface(*points, dataset=self.faceIndices)

        updates = {}

        for (vertexIndex, hit) in zip(vertexIndices, hits):

            # Evaluate which operation to perform
            #
            numFaceVertices = len(self.mesh.getFaceVertexIndices(hit.faceIndex)[0])

            if numFaceVertices == 3:

                updates[vertexIndex] = self.skin.barycentricWeights(hit.triangleVertexIndices, hit.baryCoords)

            elif numFaceVertices == 4:

                updates[vertexIndex] = self.skin.bilinearWeights(hit.faceVertexIndices, hit.biCoords)

            else:

                raise TypeError('transfer() expects 3-4 verts per face (%s found)!' % numFaceVertices)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via point on surface!')
    # endregion
