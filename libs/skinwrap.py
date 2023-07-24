import math

from scipy.spatial import cKDTree
from dataclasses import dataclass, field
from typing import List
from itertools import chain
from collections import defaultdict
from dcc import fnmesh
from dcc.dataclasses import vector
from . import abstracttransfer

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@dataclass
class ControlPoint:
    """
    Data class for interfacing with control points.
    """

    # region Fields
    index: int = 0
    point: vector.Vector = field(default_factory=vector.Vector)
    radius: float = 0.0
    vertexIndices: List[int] = field(default_factory=list)
    vertexWeights: List[float] = field(default_factory=list)
    # endregion


class SkinWrap(abstracttransfer.AbstractTransfer):
    """
    Overload of `AbstractTransfer` that transfers weights by skin wrap.
    """

    # region Dunderscores
    __slots__ = ('_falloff', '_distanceInfluence', '_faceLimit', '_controlPoints')
    __title__ = 'Skin Wrap'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :rtype: None
        """

        # Call parent method
        #
        super(SkinWrap, self).__init__(*args, **kwargs)

        # Declare private variables
        #
        self._falloff = kwargs.get('falloff', 0.0)  # type: float
        self._distanceInfluence = kwargs.get('distanceInfluence', 1.2)  # type: float
        self._faceLimit = kwargs.get('faceLimit', 3)  # type: int
        self._controlPoints = []  # type: List[ControlPoint]
    # endregion

    # region Properties
    @property
    def falloff(self):
        """
        Getter method that returns the falloff.

        :rtype: float
        """

        return self._falloff

    @property
    def distanceInfluence(self):
        """
        Getter method that returns the distance influence.

        :rtype: float
        """

        return self._distanceInfluence

    @property
    def faceLimit(self):
        """
        Getter method that returns the face limit.

        :rtype: int
        """

        return self._faceLimit
    # endregion

    # region Methods
    def computeWeight(self, distance, maxDistance):
        """
        Computes the weight for the supplied distance.

        :type distance: float
        :type maxDistance: float
        :rtype: float
        """

        # Redundancy check
        #
        if not (0.0 <= distance <= maxDistance):

            return 0.0

        # Compute weight
        #
        weight = distance / maxDistance
        adjustedWeight = 1.0 - (weight / ((math.pow(2.0, -self.falloff) - 1.0) * (1.0 - weight) + 1.0))

        return adjustedWeight

    def initializeControlPoint(self, vertexIndex, otherMesh, dataset=None):
        """
        Initializes the control point for the specified vertex.

        :type vertexIndex: int
        :type otherMesh: fnmesh.FnMesh
        :type dataset: Union[List[int], None]
        :rtype: ControlPoint
        """

        # Collect connected faces
        #
        faceIndices = set(self.mesh.getConnectedFaces(vertexIndex, componentType=self.mesh.ComponentType.Vertex))

        for i in range(1, self.faceLimit, 1):

            connectedIndices = self.mesh.getConnectedFaces(*faceIndices)
            faceIndices.update(set(connectedIndices))

        # First, convert connected faces to edges
        # Next, average the length of those face-edges
        # Finally, multiply the averaged length by our distance multiplier
        #
        edgeIndices = self.mesh.getConnectedEdges(*faceIndices, componentType=self.mesh.ComponentType.Face)
        edgeCount = len(edgeIndices)

        distance = 0.0

        for edgeIndex in edgeIndices:

            startIndex, endIndex = self.mesh.getConnectedVertices(edgeIndex, componentType=self.mesh.ComponentType.Edge)
            startPoint, endPoint = self.mesh.getVertices(startIndex, endIndex)

            distance += startPoint.distanceBetween(endPoint)

        radius = (distance / edgeCount) * self.distanceInfluence

        # Collect vertices that are within sphere of influence
        #
        vertexPoint = self.mesh.getVertices(vertexIndex, worldSpace=True)[0]
        closestIndices = otherMesh.closestVerticesInRange([vertexPoint], radius, dataset=dataset)[0]

        # Compute weights for vertices
        #
        closestPoints = otherMesh.getVertices(*closestIndices, worldSpace=True)
        distances = [vertexPoint.distanceBetween(point) for point in closestPoints]
        vertexWeights = [self.computeWeight(distance, radius) for distance in distances]

        return ControlPoint(index=vertexIndex, point=vertexPoint, radius=radius, vertexIndices=closestIndices, vertexWeights=vertexWeights)

    def closestVertexWeights(self, otherSkin, vertexIndices):
        """
        Returns the weights that are closest to the supplied skin and vertex indices.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :rtype: Dict[int, Dict[int, float]]
        """

        # Get the closest points from the point tree
        #
        points = otherSkin.controlPoints(*vertexIndices)
        pointTree = cKDTree(self.skin.controlPoints(*self.vertexIndices))

        distances, closestIndices = pointTree.query(points)

        # Get associated vertex weights
        # Remember we have to convert our local indices back to global!
        #
        closestVertexIndices = [self.vertexMap[x] for x in closestIndices]
        closestVertexWeights = self.skin.vertexWeights(*closestVertexIndices)

        updates = {vertexIndex: closestVertexWeights[closestVertexIndex] for (vertexIndex, closestVertexIndex) in zip(vertexIndices, closestVertexIndices)}

        return updates

    def transfer(self, otherSkin, vertexIndices):
        """
        Transfers the weights from this object to the supplied skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :rtype: None
        """

        # Initialize control points
        #
        otherMesh = fnmesh.FnMesh(otherSkin.intermediateObject())
        numVertices = len(self.vertexIndices)

        self._controlPoints = [None] * numVertices

        for (i, vertexIndex) in enumerate(self.vertexIndices):

            self._controlPoints[i] = self.initializeControlPoint(vertexIndex, otherMesh, dataset=vertexIndices)

        # Compute skin weights from control points
        #
        updates = {}

        for controlPoint in self._controlPoints:

            # Iterate through affected vertices
            #
            vertexWeights = self.skin.vertexWeights(controlPoint.index)

            for (vertexIndex, vertexWeight) in zip(controlPoint.vertexIndices, controlPoint.vertexWeights):

                # Check if vertex has weights
                #
                hasWeights = updates.get(vertexIndex, None) is not None

                if not hasWeights:

                    updates[vertexIndex] = defaultdict(float)

                # Apply a percentage of weights to vertex
                #
                for (influenceId, influenceWeight) in vertexWeights[controlPoint.index].items():

                    updates[vertexIndex][influenceId] += influenceWeight * vertexWeight

        # Normalize weights
        #
        updates = {vertexIndex: self.skin.normalizeWeights(vertexWeights) for (vertexIndex, vertexWeights) in updates.items()}

        # Ensure all vertices are weighted
        #
        missing = [vertexIndex for vertexIndex in vertexIndices if updates.get(vertexIndex, None) is None]
        numMissing = len(missing)

        if numMissing > 0:

            closestVertexWeights = self.closestVertexWeights(otherSkin, missing)
            updates.update(closestVertexWeights)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in updates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        updates = self.skin.remapVertexWeights(updates, influenceMap)
        otherSkin.applyVertexWeights(updates)

        log.info('Finished transferring weights via skin wrap!')
    # endregion
