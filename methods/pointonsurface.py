from itertools import chain

from dcc import fnmesh
from eztransferweights.abstract import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class PointOnSurface(abstracttransfer.AbstractTransfer):
    """
    Overload of TransferWeights that takes a skin weights object and extracts geometry based on vertex indices.
    This mesh is then used to perform barycentric/bilinear averaging.
    """

    # region Dunderscores
    __slots__ = ('_triMesh', '_faceIndices',)

    def __init__(self, *args, **kwargs):
        """
        Inherited method called after a new instance has been created.
        """

        # Call parent method
        #
        super(PointOnSurface, self).__init__(*args, **kwargs)

        # Convert vertex indices to polygons
        #
        self._triMesh = fnmesh.FnMesh(self.mesh.triMesh())
        self._faceIndices = set(self.mesh.iterConnectedFaces(*self.vertexIndices))
    # endregion

    # region Properties
    @property
    def triMesh(self):
        """
        Getter method that returns the tri-mesh function set.

        :rtype: fnmesh.FnMesh
        """

        return self._triMesh

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
        :type vertexIndices: list[int]
        :rtype: None
        """

        # Assign mesh to function set
        #
        points = otherSkin.controlPoints(*vertexIndices)
        hits = self.mesh.closestPointsOnSurface(points, faceIndices=self._faceIndices)

        updates = {}

        for (vertexIndex, hit) in zip(vertexIndices, hits):

            triangleVertexIndices = self.triMesh.faceVertexIndices(hit.hitIndex)[0]
            updates[vertexIndex] = self.skin.barycentricWeights(triangleVertexIndices, hit.hitBary)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via point on surface!')
    # endregion
