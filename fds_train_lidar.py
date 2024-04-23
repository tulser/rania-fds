import math

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import scipy.ndimage as sp_nd
import os.path as path
import pickle
import argparse

from ..src.util import convertPolarCartesian
from ..src.algs import LidarAlgSet, GlobalTrainingSets
from ..src.serialization import getCalibration
from ..src.base_config import basicConfig
from ..src.sensor import RPLidar


class FDSScanException(Exception):
    pass


DEFAULT_KNN_KEYPOINTS_NUM = 16


def scanProcessKeypoints(pts: np.ndarray) -> np.ndarray:
    # Process points into cartesian coordinates
    fil_cart_scan = convertPolarCartesian(pts)

    # Get labels
    ss = StandardScaler()
    dbs = DBSCAN(eps=LidarAlgSet.DEFAULT_DBS_EPS,
                 min_samples=LidarAlgSet.DEFAULT_DBS_MIN_SAMPLES)
    fil_cart_scan_norm = ss.fit_transform(fil_cart_scan)
    labels = dbs.fit_predict(fil_cart_scan_norm)

    # Group labels into lists representing clusters
    # First, get number of labels to allocate
    #  NOTE: Label `i` is associated with the data point at `i`.
    max_label = 0
    for i in range(0, len(labels)):
        if labels[i] > max_label:
            max_label = labels[i]

    # Create an array of lists; this method is odd but is needed to force
    #  numpy to create the array of empty lists appropriately.
    clusters = \
        np.frompyfunc(list, 0, 1)(np.empty(max_label + 1, dtype=object))
    clusters_cart = np.empty_like(clusters)
    for i in range(0, len(pts)):
        if (labels[i] != -1):
            clusters[labels[i]].append(pts[i])
            clusters_cart[labels[i]].append(fil_cart_scan[i])

    # For processing, ensure one cluster is found and used
    if (len(clusters) > 1):
        raise FDSScanException()

    cluster_select = np.array(clusters[0])
    cluster_select_cart = np.array(clusters_cart[0])

    # Get polar/degree centers of the cluster
    ctrx = sp_nd.mean(cluster_select_cart[:, 0])
    ctry = sp_nd.mean(cluster_select_cart[:, 1])
    cluster_select_ctr = np.degrees(np.arctan2(ctrx, ctry))

    # * Populate keypoints
    # Transform the cluster such that it is centered at degree 0 and in range
    # (-180, 180]
    pts_tf = np.empty_like(cluster_select)
    for i in range(0, len(cluster_select)):
        cpt = cluster_select[i][0] - cluster_select_ctr
        if cpt > 180:
            pts_tf[i][0] = cpt - 360
        else:
            pts_tf[i][0] = cpt
        pts_tf[i][1] = cluster_select[i][1]

    # Get the span of the angle of the measurements in the cluster
    pts_deg_span = pts_tf[:, 0].max() - pts_tf[:, 0].min()

    # Get section lengths for each keypoint to average from
    pts_sec_len = pts_deg_span / DEFAULT_KNN_KEYPOINTS_NUM
    start_idx = 0
    end_idx = 0
    keypoints = np.empty(16, dtype=float)
    for i in range(0, len(keypoints) - 1):
        pts_sec_end = math.floor((i + 1) * pts_sec_len)
        # Get an interval
        for j in range(start_idx, len(pts_tf)):
            if pts_tf[j] > pts_sec_end:
                end_idx = j
        pts_sec = pts_tf[start_idx:end_idx]
        # Get the mean distance for the keypoint
        keypoints[i] = sp_nd.mean(pts_sec[:, 1])
        start_idx = end_idx
    # For final keypoint, just use all remaining points
    pts_sec = pts_tf[start_idx:len(pts_tf)]
    # Get the mean distance for the keypoint
    keypoints[i] = sp_nd.mean(pts_sec[:, 1])

    return keypoints


SCANS_MAX = 5


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trainpath", type=str, nargs=1, action="store")
    parser.add_argument("label", type=int, nargs=1, action="store")

    args = parser.parse_args()

    tolabel = args.label
    trainpath = args.trainpath

    if not path.exists(trainpath):
        training = GlobalTrainingSets(DEFAULT_KNN_KEYPOINTS_NUM, [], [])
    else:
        with open(trainpath, "rb") as file:
            obj = pickle.load(file)
        if not isinstance(obj, GlobalTrainingSets):
            raise IOError()
        training = obj

    # Initialize sensor
    config = basicConfig()
    calibration_data = getCalibration(config.sensors[0].calibration_path)
    # Using specific sensor 0
    sensor = RPLidar(config.sensors[0], calibration_data)
    sensor.startScanning()

    # Get scans of the environment
    scan_list = []
    for i in range(0, SCANS_MAX):
        scan_list.append(sensor.getRawSamples())
    # Merge scans into one set
    scan_all = np.concatenate(scan_list, axis=0)
    # The array is sorted to make bounds calculation easier
    scan_all = np.sort(scan_all, axis=0)

    (scan_all_fil, _) = sensor.filterSamples(scan_all)

    new_keypoints = scanProcessKeypoints(scan_all_fil)
    training.clsf_lidar_knn_set_kpdata.append(new_keypoints)
    training.clsf_lidar_knn_set_labels.append(tolabel)

    return


if __name__ == "__main__":
    main()
