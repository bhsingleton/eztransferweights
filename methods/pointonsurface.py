from ..abstract import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class PointOnSurface(abstracttransfer.AbstractTransfer):
    """
    Overload of TransferWeights that takes a skin weights object and extracts geometry based on vertex indices.
    This mesh is then used to perform barycentric/bilinear averaging.
    """

    __slots__ = ('_faceIndices',)

    def __init__(self, *args, **kwargs):
        """
        Inherited method called after a new instance has been created.
        """

        # Call parent method
        #
        super(PointOnSurface, self).__init__(*args, **kwargs)

        # Convert vertex indices to polygons
        #
        self._faceIndices = list(self.mesh.iterConnectedFaces(*self.vertexIndices))

    @property
    def faceIndices(self):
        """
        Getter method that returns the cached face indices.

        :rtype: list[int]
        """

        return self._faceIndices

    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: list[int]
        :rtype: None
        """

        # Assign mesh to function set
        #
        points = otherSkin.controlPoints(*vertexIndices)
        hits = self.mesh.closestPointsOnSurface(points, self._faceIndices)

        updates = {}

        for (vertexIndex, hit) in zip(vertexIndices, hits):

            triangleVertexIndices = self.mesh.triangleVertexIndices(hit.hitIndex)
            updates[vertexIndex] = self.skin.barycentricWeights(triangleVertexIndices[hit.hitIndex], hit.hitBary)

        # Remap source weights to target
        #
        influenceMap = self.skin.createInfluenceMap(otherSkin, vertexIndices=self.vertexIndices)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via point on surface!')
