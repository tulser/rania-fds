import numpy as np

from scipy.spatial import cKDTree


def hausdorffDistanceFast(cluster1, cluster2):
    tree1 = cKDTree(cluster1)
    distances, _ = tree1.query(cluster2)
    max_distance = np.max(distances)
    return max_distance
