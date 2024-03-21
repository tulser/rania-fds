from typing import (List, Tuple)

from enum import Enum
import logging
import threading
from collections import deque
import time

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.neighbors import KNeighborsClassifier

import sensor
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

        # control over starting the room is managed by the owning domain
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

    def __getLidarClusters(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get clusters from filtered scans.
        :returns Tuple[np.ndarray, np.ndarray]: A set of clustered and
            unclustered data, respectively.
        """

        # Get labels
        
        fil_scan_norm = self.__ss.fit_transform(self._fil_scans[0])
        labels = dbs.fit_predict(fil_scan_norm)
        # Group labels into lists representing clusters
        # First, get number of labels to allocate
        #  NOTE: Label `i` is associated with the data point at `i`.
        max_label = 0
        for i in range(0, len(labels)):
            if labels[i] > max_label:
                max_label = labels[i]

        unclustered = []
        clusters = np.full(max_label, [], dtype=list)
        for i in range(0, len(labels)):
            if (labels[i] == -1):
                unclustered.append(self._fil_scans[0][i])
            else:
                clusters[labels[i]].append(self._fil_scans[0][i])

        return (clusters, np.array(unclustered))

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
        (lidar_clusters, _) = self.__getLidarClusters()
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

    def __classificationProcessHigh(self):
        """
        Use a higher power/intensity classification algorithm in the HIGH
        activity state to find falls in a room with continued activity.
        """

        self._activity_state = FDSRoom.ActivityState.HIGH
        # TODO: Run KNN here to process scan which caused changeover
        # Check for occupancy to ensure there exists clusters to process
        (lidar_clusters, _) = self.__getLidarClusters()
        while (len(lidar_clusters) != 0):
            # TODO: Use mutex to pause thread
            # TODO: run KNN
            pass
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
        self.__dbs = DBSCAN(eps=0.5, min_samples=10)
        self.__ss = StandardScaler()
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
