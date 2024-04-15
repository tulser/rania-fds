from typing import List, Iterable

from enum import Enum, auto
import logging
import threading
from collections import deque
import time

import numpy as np

import sensor
import algs
from .domain import FDSDomain
from .fdscommon import FDSRoomConfig, FDSException


class FDSRoom(object):
    """
    Class representing a room/spacial unit of an FDSDomain.
    """

    class ActivityState(Enum):
        """
        Enumeration of activity/processing states representing the state of
        processing and activity/occupancy.
        """

        NONE = auto()
        PAUSED = auto()
        LOW = auto()
        HIGH = auto()

    __SENSOR_THREAD_TIMEOUT_SEC = 2.0
    __SCAN_MIN_WINDOW_SIZE = 5
    __LOW_CLASSIFY_PERIOD_SEC = 0.7

    def __init__(self, room_config: FDSRoomConfig, domain_owner: FDSDomain,
                 logger: logging.Logger):
        """
        :param room_config: A room specific configuration to use.
        :type room_config: FDSRoomConfig
        :param domain_owner: The domain object that owns this room.
        :type domain_owner: FDSDomain
        :param logger: The logger to use for logging.
        :type logger: logging.Logger
        """

        self.__config = room_config
        self.__domain = domain_owner
        self.__logger = logger
        self.__scans = np.ndarray(self._WINDOW_SIZE)
        self.__sensors = sensor.getRoomSensors(room_config, logger)
        self.__lidar_sensors = []
        self.__lidar_calibration = []
        for s in self._sensors:
            if isinstance(s, sensor.RPLidar):
                self.__lidar_sensors.append(s)

        # Initialize algorithms with parameters
        # TODO: Need complete parameter set
        self.__lidar_algs = algs.LidarAlgSet(dbs_eps=0.5,
                                             dbs_min_samples=6)

        # Execution control over the room is managed by the owning domain
        domain_owner.addThread(target=self.__thread_classification,
                               name="FDS Classification Thread")
        return

    def pauseThreads(self):
        """
        Pause threads in this room.
        """

        if self._activity_state is self.ActivityState.NONE:
            raise FDSException()

        self.__pause_event.clear()
        return

    def resumeThreads(self):
        """
        Resume threads in this room.
        """

        if self._activity_state is self.ActivityState.NONE:
            raise FDSException()

        if self._activity_state is self.ActivityState.PAUSED:
            self.__pause_event.set()
            return
        raise FDSException()

    def __checkPause(self) -> True:
        """
        Cause the thread to wait if the event has yet to be set (to resume).
        :return: True if the thread had paused, false otherwise.
        :rtype: bool
        """

        if not self.__pause_event.is_set():
            self._activity_state = self.ActivityState.PAUSED
            self.__pause_event.wait(timeout=None)
            return True
        return False

    def __thread_sensorScanPull(self):
        """
        Thread function.
        Asynchronously buffer sensor scans from `__thread_sensorScan` to feed
        to `__thread_classification`.
        """

        while self._sensor_sentinel:
            
        return 0

    def __thread_sensorScan(self):
        """
        Thread function.
        Get sensor scans and data asynchronously and continuously, spawned by
        `__thread_classification()`.
        """

        # Initialize queues
        self._fil_scans: List[deque] = []
        for lidar in self._lidar_sensors:
            lidar.startScanning()
            self._fil_scans.append(deque(
                iterable=[],
                maxlen=FDSRoom._SCAN_MIN_WINDOW_SIZE))

        # Begin sensor sampling/scan loop
        lidars_size: int = len(self._lidar_sensors)
        while self._sensor_sentinel:
            self.__pause_event.wait(timeout=None)

            # Add to window
            for i in range(0, lidars_size):
                lidar = self._lidar_sensors[i]
                self._fil_scans[i].append(lidar.getFilteredData())

        for lidar in self._lidar_sensors:
            lidar.stopScanning()

        self._sensor_sentinel = True  # Reset to true for exit
        return 0

    def __pullLidarData(self) -> Iterable[np.ndarray]:
        """
        Pull sensor scans generated by the sensorScan thread.

        :return: An ordered list of raw scans, ordered by increasing degree.
        :rtype: Iterable[np.ndarray]
        """

        with self.__sensor_pull_lock:
        return

    def __classificationProcessLow(self):
        """
        Use a low power/intensity classification algorithm in the LOW activity
        state to find some activity in the room. This algorithm attempts to
        simply cluster the filtered data and find some clusters, with a minimum
        number of points, before switching to the HIGH activity state and
        exiting.
        """

        self._activity_state = self.ActivityState.LOW

        # Get lidar data
        self.__pullLidarData()

        # Check for occupancy
        (lidar_clusters, _) = \
            self.__lidar_algs.clusterLidarScan(self._fil_scans)

        time_tosleep = time.monotonic()
        while (len(lidar_clusters) == 0):
            # TODO: use Event synchronization to (un)pause thread
            (lidar_clusters, _) = \
                self.__lidar_algs.clusterLidarScan(self._fil_scans)

            time_tosleep = self.__LOW_CLASSIFY_PERIOD_SEC - \
                (time.monotonic() - time_tosleep)
            time.sleep(time_tosleep)

            self.__checkPause()

            time_tosleep = time.monotonic()

        # Set the next state/function to transition to.
        self.__classificationProcess = self.__classificationProcessHigh
        return 0

    def __classificationProcessHigh(self):
        """
        Use a higher power/intensity classification algorithm in the HIGH
        activity state to find falls in a room with continued activity.
        """

        self._activity_state = self.ActivityState.HIGH

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
                    self.__domain._emitFallEvent(self.__config.id)
                    break

            self.__checkPause()

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

        # Construct synchronization primitizes
        self.__pause_event = threading.Event()
        self.__sensor_pull_lock = threading.Lock()

        # Room thread controls sensor thread, not the pool
        sensor_thread = threading.Thread(target=self.__thread_sensorScan,
                                         name="FDS Sensor Data Pull Loop")
        self._sensor_sentinel = True
        sensor_thread.run()

        # Begin fall detection processing loop using low power classification
        self._activity_state = self.ActivityState.LOW
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
        sensor_thread.join(self.__SENSOR_THREAD_TIMEOUT_SEC)
        if (not self._sensor_sentinel):
            self._logger.debug("Sensor thread did not join promptly, exceeded "
                               "{0} seconds"
                               .format(self.__SENSOR_THREAD_TIMEOUT_SEC))
        return 0
