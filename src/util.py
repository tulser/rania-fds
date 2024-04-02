import numpy as np
from scipy.spatial import cKDTree


def hausdorffDistanceFast(cluster1, cluster2):
    tree1 = cKDTree(cluster1)
    distances, _ = tree1.query(cluster2)
    max_distance = np.max(distances)
    return max_distance


def convertPolarCartesian(pts: np.ndarray) -> np.ndarray:
    x = pts[:, 0] * np.cos(np.radians(pts[:, 1]))
    y = pts[:, 0] * np.sin(np.radians(pts[:, 1]))
    return np.ndarray([x, y])
