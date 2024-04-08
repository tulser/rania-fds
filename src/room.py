from typing import List

from enum import Enum
import logging
import threading
from collections import deque
import time

import numpy as np

import sensor
import algs
from .domain import FDSDomain
from .fdscommon import FDSRoomConfig, FDSThreadPool, FDSException


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

    def __init__(self, room_config: FDSRoomConfig, parent_domain: FDSDomain,
                 thread_pool: FDSThreadPool, logger: logging.Logger):
        self._roomconfig = room_config
        self._domain = parent_domain
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

        # Initialize algorithms with parameters
        self.__lidar_algs = algs.LidarAlgSet(dbs_eps=0.5, dbs_min_samples=6)

        # Execution control over the room is managed by the owning domain
        parent_domain._thread_pool.addThread(
            target=self.__thread_classification)
        parent_domain._thread_pool.addThread(
            target=self.__thread_sensorscan)

    def __thread_sensorscan(self):
        """
        Thread function.
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
        (lidar_clusters, _) = \
            self.__lidar_algs.clusterLidarScan(self._fil_scans)

        time_tosleep = time.monotonic()
        while (len(lidar_clusters) == 0):
            # TODO: use Event synchronization to (un)pause thread
            (lidar_clusters, _) = \
                self.__lidar_algs.clusterLidarScan(self._fil_scans)

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
        (lidar_clusters, _) = \
            self.__lidar_algs.clusterLidarScanAdv(self._fil_scans)

        while (len(lidar_clusters) != 0):
            # TODO: use Event synchronization to (un)pause thread
            # Process each cluster
            for cluster in lidar_clusters:
                # Process key samples
                cluster_pts = cluster[0]
                center = cluster[1]
                activity = \
                    self.__lidar_algs.classifyLidarCluster(cluster_pts, center)
                if (activity == 1):  # fall detected
                    self._domain._roomEmitFallEvent(self._roomconfig.id)
                    break

            # Keep checking for occupancy
            (lidar_clusters, _) = \
                self.__lidar_algs.clusterLidarScanAdv(self._fil_scans)

        # Set the next state/function to transition to.
        self.__classificationProcess = self.__classificationProcessHigh
        return 0

    def __thread_classification(self):
        """
        Thread function.
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
        # TODO: remove this, migrate algorithms to algs.py
        # self.__lidar_knn = KNeighborsClassifier(n_neighbors=6,
        #                                        algorithm='ball_tree',
        #                                        p=1)

        # TODO: pass training data
        # self.__lidar_knn = self.__lidar_knn.fit(training data, labels)
        # Beginfall detection processing loop using low power classification
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
                               "{0} seconds"
                               .format(FDSRoom._SENSOR_THREAD_TIMEOUT))
        return 0
