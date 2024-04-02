from typing import (List, Tuple)

from enum import Enum
import logging
import threading
from collections import deque
import time
import math

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.neighbors import KNeighborsClassifier
import scipy as sp

import sensor
import util
from fdscommon import (FDSRoomConfig, FDSThreadPool, FDSException)


class FDSRoom(object):
    """
    Class representing a room/spacial unit of an FDSDomain
    """

    class ActivityState(Enum):
        """
        Enumeration of activity/processing states to convey processing state to
        a connected RANIA hub (or programs/services in general).
        """

        NONE = 0
        LOW = 1
        HIGH = 2

    _SENSOR_THREAD_TIMEOUT_SEC = 2.0
    _SCAN_MIN_WINDOW_SIZE = 5
    _LOW_CLASSIFY_PERIOD_SEC = 0.7
    _LIDAR_KNN_KEY_SAMPLES_NUM = 16

    def __init__(self, room_config: FDSRoomConfig, thread_pool: FDSThreadPool,
                 logger: logging.Logger):
        self._roomconfig = room_config
        self._thread_pool = thread_pool
        self._logger = logger
        self._scans = np.ndarray(self._WINDOW_SIZE)
        self._sensors = sensor.getRoomSensors(room_config, logger)
        self._lidar_sensors = []
        self._lidar_calibration = []
        for s in self._sensors:
            if isinstance(s, sensor.RPLidar):
                self._lidar_sensors.append(s)
                self._lidar_geom_bounds.append(s.getCalibration().bounds)

        # Execution control over the room is managed by the owning domain
        self._threadpool.addThread(target=self.__thread_classification)

    def __thread_sensordata(self):
        """
        Get sensor scans and data asynchronously and continuously, spawned by
        `__thread_classification()`.
        """

        # initialization
        self._fil_scans: List[deque] = []
        for lidar in self._lidar_sensors:
            lidar.startScanning()
            self._fil_scans.append(deque(
                iterable=[],
                maxlen=FDSRoom._SCAN_MIN_WINDOW_SIZE))

        # begin scanning loop
        lidars_size: int = len(self._lidar_sensors)
        while self._sensor_sentinel:
            # TODO: pause thread
            # Add to window
            for i in range(0, lidars_size):
                lidar = self._lidar_sensors[i]
                self._fil_scans[i].append(lidar.getFilteredData())

        for lidar in self._lidar_sensors:
            lidar.stopScanning()

        self._sensor_sentinel = True  # confirm for exit
        return 0

    def __getLidarClusters(self, pts: np.ndarray
                           ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get clusters from filtered polar scans.
        :returns Tuple[np.ndarray, np.ndarray]: A set of clustered and
            unclustered data, respectively.
        """

        # Process points into cartesian coordinates
        fil_cart_scan = util.convertPolarCartesian(pts[0])

        # Get labels
        fil_cart_scan_norm = self.__ss.fit_transform(fil_cart_scan)
        labels = self.__lidar_dbs.fit_predict(fil_cart_scan_norm)

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
        clusters = np.frompyfunc(list, 0, 1)(np.empty(max_label + 1, dtype=object))
        clusters_cart = np.empty_like(clusters)
        for i in range(0, len(pts[0])):
            if (labels[i] != -1):
                clusters[labels[i]].append(pts[0][i])
                clusters_cart[labels[i]].append(fil_cart_scan[i])
            else:
                unclustered.append(pts[0][i])

        clusters_np = np.empty_like(clusters, dtype=np.ndarray)
        clusters_cart_np = np.empty_like(clusters_np)
        for i in range(0, len(clusters)):
            clusters_np[i] = np.array(clusters[i])
            clusters_cart_np[i] = np.array(clusters_cart[i])

        # Get polar/degree centers of the clusters, also get centers of
        #  clusters in polar space using corresponding cartesian points
        clusters_ctrs = np.empty_like(clusters, dtype=float)
        for i in range(0, len(clusters)):
            ctrx = sp.ndimage.mean(clusters_cart_np[i][:, 0])
            ctry = sp.ndimage.mean(clusters_cart_np[i][:, 1])
            c = np.degrees(np.arctan2(ctrx, ctry))
            clusters_ctrs[i] = (c + 360) if (c < 0) else c

        return (clusters_np, clusters_ctrs, np.array(unclustered))

    def __classificationProcessLow(self):
        """
        Use a low power/intensity classification algorithm in the LOW activity
        state to find some activity in the room. This algorithm attempts to
        simply cluster the filtered data and find some clusters, with a minimum
        number of points, before switching to the HIGH activity state and
        exiting.
        """

        self._activity_state = FDSRoom.ActivityState.LOW
        # Check for occupancy
        (lidar_clusters, _) = self.__getLidarClusters(self._fil_scans)
        time_tosleep = time.monotonic()
        while (len(lidar_clusters) == 0):
            # TODO: use mutex to pause thread
            time_tosleep = FDSRoom._LOW_CLASSIFY_PERIOD_SEC - \
                (time.monotonic() - time_tosleep)
            time.sleep(time_tosleep)
            time_tosleep = time.monotonic()

        # Set the next state/function to transition to.
        self.__classificationProcess = self.__classificationProcessHigh
        return 0

    def __getLidarActivityHigh(self, cluster: np.ndarray, ctrs: np.ndarray
                               ) -> int:
        keypoints = np.empty(FDSRoom._LIDAR_KNN_KEY_SAMPLES_NUM, dtype=float)

        self.__lidar_knn

        return 0

    def __classificationProcessHigh(self):
        """
        Use a higher power/intensity classification algorithm in the HIGH
        activity state to find falls in a room with continued activity.
        """

        self._activity_state = FDSRoom.ActivityState.HIGH
        # TODO: Run KNN here to process scan which caused changeover
        # Check for occupancy to ensure there exists clusters to process
        (lidar_clusters, lidar_clusters_ctrs, _) = self.__getLidarClusters(self._fil_scans)
        while (len(lidar_clusters) != 0):
            # TODO: Use mutex to pause thread
            # Process each cluster
            for cluster in lidar_clusters:
                # Process key samples
                cluster_np = np.array(cluster)
                activity = self.__getLidarActivityHigh(cluster_np)
                if (activity == 1):  # fall detected
                    # TODO: Emit event
                    pass

            # Keep checking for occupancy
            (lidar_clusters, lidar_clusters_ctrs, _) = self.__getLidarClusters(self._fil_scans)

        # Set the next state/function to transition to.
        self.__classificationProcess = self.__classificationProcessHigh
        return 0

    def __thread_classification(self):
        """
        Process data from sensor scans, spawned and started by thread pool.
        This function controls state transitions for different classification
        modes.
        """
        # function to run in its own thread for real-time processing
        # room thread controls sensor thread
        sensor_thread = threading.Thread(target=self._sensorThread)
        self._sensor_sentinel = True
        sensor_thread.run()
        # Initialize needed scikit objects for persistance
        self.__lidar_dbs = DBSCAN(eps=0.5, min_samples=6)
        self.__ss = StandardScaler()
        self.__lidar_knn = KNeighborsClassifier(n_neighbors=6,
                                                algorithm='ball_tree',
                                                p=1)
        # TODO: pass training data
        # self.__lidar_knn = self.__lidar_knn.fit(training data, labels)
        # Begin fall detection processing loop using low power classification
        self._activity_state = FDSRoom.ActivityState.LOW
        self.__classificationProcess = self.__classificationProcessLow
        # Run loop, classificationProcess method pointer is set in
        #  classification process
        while True:
            try:
                exit_status = self.__classificationProcess()
                if (exit_status != 0):  # start graceful exit
                    break
            except FDSException as err:
                raise err

        self._sensor_sentinel = False
        sensor_thread.join(FDSRoom._SENSOR_THREAD_TIMEOUT_SEC)
        if (not self._sensor_sentinel):
            self._logger.debug("Sensor thread did not join promptly, exceeded "
                               "{0} seconds" % FDSRoom._SENSOR_THREAD_TIMEOUT)
        return 0
