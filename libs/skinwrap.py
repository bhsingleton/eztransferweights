import math

from dataclasses import dataclass, field
from typing import List, Dict
from itertools import chain
from collections import defaultdict
from scipy.spatial import cKDTree
from dcc import fnmesh
from dcc.math import skinmath
from dcc.dataclasses.vector import Vector
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
    point: Vector = field(default_factory=Vector)
    radius: float = 0.0
    vertexIndices: List[int] = field(default_factory=list)
    vertexWeights: List[float] = field(default_factory=list)
    # endregion


class SkinWrap(abstracttransfer.AbstractTransfer):
    """
    Overload of `AbstractTransfer` that transfers weights by skin wrap.
    """

    # region Dunderscores
    __slots__ = ('_falloff', '_distanceInfluence', '_faceLimit', '_controlPoints', '_otherPoints', '_otherPointTree', '_otherVertexMap')
    __title__ = 'Skin Wrap'

    def __init__(self, *args, **kwargs):
        """
        Private method called after a new instance has been created.

        :type args: Union[Tuple[fnskin.FnSkin], Tuple[fnskin.FnSkin, List[int]]]
        :key falloff: float
        :key distanceInfluence: float
        :key faceLimit = int
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
        self._otherPoints = []  # type: List[Vector]
        self._otherPointTree = None  # type: cKDTree
        self._otherVertexMap = {}  # type: Dict[int, int]
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

    def initializeControlPoint(self, vertexIndex):
        """
        Initializes the control point for the specified vertex.

        :type vertexIndex: int
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
        closestIndices = self._otherPointTree.query_ball_point([vertexPoint], radius)[0]
        vertexIndices = list(map(self._otherVertexMap.get, closestIndices))

        # Compute weights for vertices
        #
        closestPoints = [self._otherPoints[closestIndex] for closestIndex in closestIndices]
        distances = [vertexPoint.distanceBetween(point) for point in closestPoints]
        vertexWeights = [self.computeWeight(distance, radius) for distance in distances]

        return ControlPoint(index=vertexIndex, point=vertexPoint, radius=radius, vertexIndices=vertexIndices, vertexWeights=vertexWeights)

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
        closestVertexIndices = [self.localVertexMap[x] for x in closestIndices]
        closestVertexWeights = self.skin.vertexWeights(*closestVertexIndices)

        updates = {vertexIndex: closestVertexWeights[closestVertexIndex] for (vertexIndex, closestVertexIndex) in zip(vertexIndices, closestVertexIndices)}

        return updates

    def transfer(self, otherSkin, vertexIndices, notify=None):
        """
        Transfers the weights from this skin to the other skin.

        :type otherSkin: fnskin.FnSkin
        :type vertexIndices: List[int]
        :type notify: Union[Callable, None]
        :rtype: None
        """

        # Initialize control points
        #
        otherMesh = fnmesh.FnMesh(otherSkin.intermediateObject())
        self._otherPoints = otherMesh.getVertices(*vertexIndices, worldSpace=True)
        self._otherPointTree = cKDTree(self._otherPoints)
        self._otherVertexMap = dict(enumerate(vertexIndices))

        numControlPoints = len(self.vertexIndices)
        self._controlPoints = [None] * numControlPoints

        progressFactor = 100.0 / float(numControlPoints)

        for (i, vertexIndex) in enumerate(self.vertexIndices):

            # Initialize control point
            #
            self._controlPoints[i] = self.initializeControlPoint(vertexIndex)

            # Signal progress update
            #
            if callable(notify):

                progress = int(math.ceil((float(i + 1) * progressFactor * 0.5)))
                notify(progress)

        # Compute skin weights from control points
        #
        updates = {}

        for (i, controlPoint) in enumerate(self._controlPoints, start=1):

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

            # Signal progress update
            #
            if callable(notify):

                progress = 50 + int(math.ceil((float(i + 1) * progressFactor * 0.5)))
                notify(progress)

        # Normalize weights
        #
        maxInfluences = otherSkin.maxInfluences()
        normalizedUpdates = {}

        for (vertexIndex, vertexWeights) in updates.items():

            try:

                normalizedUpdates[vertexIndex] = skinmath.normalizeWeights(vertexWeights, maxInfluences=maxInfluences)

            except TypeError:  # Reserved for zero weights!

                continue

        # Ensure all vertices are weighted
        #
        missing = [vertexIndex for vertexIndex in vertexIndices if normalizedUpdates.get(vertexIndex, None) is None]
        numMissing = len(missing)

        if numMissing > 0:

            closestVertexWeights = self.closestVertexWeights(otherSkin, missing)
            normalizedUpdates.update(closestVertexWeights)

        # Remap source weights to target
        #
        influenceIds = set(chain(*[list(x.keys()) for x in normalizedUpdates.values()]))
        influenceMap = self.skin.createInfluenceMap(otherSkin, influenceIds=influenceIds)

        normalizedUpdates = self.skin.remapVertexWeights(normalizedUpdates, influenceMap)
        otherSkin.applyVertexWeights(normalizedUpdates)

        log.info('Finished transferring weights via skin wrap!')
    # endregion
