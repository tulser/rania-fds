from typing import List, Tuple
from enum import Enum, auto

import math

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.neighbors import KNeighborsClassifier
import numpy as np
import scipy.ndimage as sp_nd

import util


class LidarAlgSet(object):

    def __init__(self, clsf_knn_traindata: np.ndarray,
                 dbs_eps: float = 0.5,
                 dbs_min_samples: int = 6,
                 clsf_knn_neighbors: int = 6,
                 clsf_key_points_n: int = 16):
        self.__dbs = DBSCAN(eps=dbs_eps, min_samples=dbs_min_samples)
        self.__ss = StandardScaler()
        self.__knn_clsf = KNeighborsClassifier(n_neighbors=clsf_knn_neighbors,
                                               algorithm='ball_tree',
                                               p=1)
        knn_data = clsf_knn_traindata[0]
        knn_labels = clsf_knn_traindata[1]
        self.__knn_clsf.fit(knn_data, knn_labels)

        self._clsf_key_points_n = clsf_key_points_n
        # preallocate array for key points
        self.__keypoints = np.empty(self._clsf_key_points, dtype=float)

        return

    class ActivityClass(Enum):
        OTHER = auto()
        FALL = auto()

    def classifyLidarCluster(self, pts: np.ndarray, pts_ang_ctr: float
                             ) -> ActivityClass:
        """
        Classify activity with the given set of Lidar points.

        :param np.ndarray pts: An array of points of shape (n_points, 2)
            with the latter dimension of form (degree, distance).
        :param float pts: The angular center of the cluster in degrees within
            the range of [0-360).
        :return: A predicted label for the input cluster.
        :rtype: ActivityClass
        """

        # Note: Recall that the index of `pts` does not correspond to degree;
        #   however, points from a scan generally have increasing degrees.

        # * Populate keypoints
        # Transform the input cluster such that it is centered at degree 0
        pts_tf = np.empty_like(pts)
        pts_tf[:, 0] = pts[:, 0] - pts_ang_ctr
        pts_tf[:, 1] = pts[:, 1]
        # Get the span of the angle of the measurements in the cluster
        pts_deg_span = pts_tf[:, 0].max() - pts_tf[:, 0].min()
        # Get section lengths for each keypoint to average from
        pts_sec_len = pts_deg_span / self._clsf_key_points_n
        start_idx = 0
        end_idx = 0
        for i in range(0, len(self.__keypoints) - 1):
            pts_sec_end = math.floor((i + 1) * pts_sec_len)
            # Get an interval
            for j in range(start_idx, len(pts_tf)):
                if pts_tf[j] > pts_sec_end:
                    end_idx = j
            pts_sec = pts_tf[start_idx:end_idx]
            # Get the mean distance for the keypoint
            self.__keypoints[i] = sp_nd.mean(pts_sec[:, 1])
            start_idx = end_idx
        # For final keypoint, just use all remaining points
        pts_sec = pts_tf[start_idx:len(pts_tf)]
        # Get the mean distance for the keypoint
        self.__keypoints[i] = sp_nd.mean(pts_sec[:, 1])

        # * Pass keypoints as data point to KNeighborsClassifier
        label = self.__knn_clsf.predict(self.__keypoints)

        return label

    def clusterLidarScan(self, pts: np.ndarray
                         ) -> Tuple[List[np.ndarray], np.ndarray]:
        """
        Get clusters from Lidar scans.

        :param pts: An array of points of shape (n_points, 2) with the latter
            dimension of form (degree, distance).
        :return: A tuple of clustered points and unclustered points,
            respectively. Clustered points have shape (n_clusters) which
            contain arrays of variable lengths.
        """

        # Process points into cartesian coordinates
        fil_cart_scan = util.convertPolarCartesian(pts[0])

        # Get labels
        fil_cart_scan_norm = self.__ss.fit_transform(fil_cart_scan)
        labels = self.__dbs.fit_predict(fil_cart_scan_norm)

        # Group labels into lists representing clusters
        # First, get number of labels to allocate
        #  NOTE: Label `i` is associated with the data point at `i`.
        max_label = 0
        for i in range(0, len(labels)):
            if labels[i] > max_label:
                max_label = labels[i]

        unclustered = []
        # Create an array of lists; this method is odd but is needed to force
        #  numpy to create the array of empty lists appropriately.
        clusters = \
            np.frompyfunc(list, 0, 1)(np.empty(max_label + 1, dtype=object))
        for i in range(0, len(pts[0])):
            if (labels[i] != -1):
                clusters[labels[i]].append(pts[0][i])
            else:
                unclustered.append(pts[0][i])

        clusters_list = []
        for cluster in clusters:
            clusters_list.append(cluster)

        return (clusters_list, np.array(unclustered))

    def clusterLidarScanAdv(self, pts: np.ndarray
                            ) -> Tuple[List[Tuple[np.ndarray, float]],
                                       np.ndarray]:
        """
        Get clusters from Lidar scans, getting additional cluster centers for
        high power processing.

        :param pts: An array of points of shape (n_points, 2) with the latter
            dimension of form (degree, distance).
        :return: A tuple of clustered data, cluster centers in angular degrees,
            and unclustered data, respectively.
        """

        # Process points into cartesian coordinates
        fil_cart_scan = util.convertPolarCartesian(pts[0])

        # Get labels
        fil_cart_scan_norm = self.__ss.fit_transform(fil_cart_scan)
        labels = self.__dbs.fit_predict(fil_cart_scan_norm)

        # Group labels into lists representing clusters
        # First, get number of labels to allocate
        #  NOTE: Label `i` is associated with the data point at `i`.
        max_label = 0
        for i in range(0, len(labels)):
            if labels[i] > max_label:
                max_label = labels[i]

        unclustered = []
        # Create an array of lists; this method is odd but is needed to force
        #  numpy to create the array of empty lists appropriately.
        clusters = \
            np.frompyfunc(list, 0, 1)(np.empty(max_label + 1, dtype=object))
        clusters_cart = np.empty_like(clusters)
        for i in range(0, len(pts[0])):
            if (labels[i] != -1):
                clusters[labels[i]].append(pts[0][i])
                clusters_cart[labels[i]].append(fil_cart_scan[i])
            else:
                unclustered.append(pts[0][i])

        clusters_cart_np = np.empty_like(clusters)
        for i in range(0, len(clusters)):
            clusters_cart_np[i] = np.array(clusters_cart[i])

        clusters_tlist = []

        # Get polar/degree centers of the clusters, also get centers of
        #  clusters in polar space using corresponding cartesian points
        for i in range(0, len(clusters)):
            ctrx = sp_nd.mean(clusters_cart_np[i][:, 0])
            ctry = sp_nd.mean(clusters_cart_np[i][:, 1])
            c = np.degrees(np.arctan2(ctrx, ctry))
            cluster_ctr = (c + 360) if (c < 0) else c
            clusters_tlist.append((clusters[i], cluster_ctr))

        return (clusters_tlist, np.array(unclustered))
