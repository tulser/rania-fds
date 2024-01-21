import numpy as np

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from .misc import hausdorffDistanceFast


def clusterConvert(scan):
    # Convert data to a numpy array

    data_array = np.array(scan)
    # print(data_array.shape)

    # Normalize the data
    data_normalized = StandardScaler().fit_transform(data_array)

    # Create a DBSCAN instance
    dbscan = DBSCAN(eps=0.35, min_samples=10)

    # Fit the normalized data to the algorithm
    labels = dbscan.fit_predict(data_normalized)

    return labels


def separateClusters(data, labels):
    # Create an empty dictionary to hold clusters
    clusters = {}

    # Iterate through data points and labels
    for point, label in zip(data, labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(point)

    return clusters


def checkClosestClusters(new_clusters, old_clusters):
    updated_clusters = {}

    for new_label, new_cluster in new_clusters.items():
        min_distance = float('inf')
        closest_label = None

        for old_label, old_cluster in old_clusters.items():
            distance = hausdorffDistanceFast(new_cluster, old_cluster)

            if distance < min_distance:
                min_distance = distance
                closest_label = old_label

        if closest_label is not None and min_distance < 2:
            updated_clusters[new_label] = old_clusters[closest_label]
        else:
            updated_clusters[new_label] = new_cluster

    return updated_clusters
