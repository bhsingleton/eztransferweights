from scipy.spatial import cKDTree

from ..abstract import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class PointCloud(abstracttransfer.AbstractTransfer):
    """
    Overload of TransferWeights used to turn geometry into a point cloud.
    This data is then used for closest point transfer.
    """

    __slots__ = ('vertexMap', 'points', 'tree')

    def __init__(self, *args, **kwargs):
        """
        Overloaded method called after a new instance has been created.
        """

        # Call parent method
        #
        super(PointCloud, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self.vertexMap = dict(enumerate(self.vertexIndices))
        self.points = self.skin.controlPoints(*self.vertexIndices)
        self.tree = cKDTree(self.points)

    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: list[int]
        :rtype: None
        """

        # Get closest points and compose new dictionary
        #
        points = otherSkin.controlPoints(*vertexIndices)
        distances, closestIndices = self.tree.query(points)

        # Collect vertex weights
        # Remember we gotta convert our local indices back to global!
        #
        closestVertexIndices = [self.vertexMap[x] for x in closestIndices]
        closestVertices = self.skin.vertexWeights(*closestVertexIndices)

        updates = {vertexIndex: closestVertices[closestVertexIndex] for (vertexIndex, closestVertexIndex) in zip(vertexIndices, closestVertexIndices)}

        # Remap source weights to target
        #
        influenceMap = self.skin.createInfluenceMap(otherSkin, vertexIndices=self.vertexIndices)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via point cloud!')
