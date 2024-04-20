from typing import List, Iterable

from enum import Enum, auto
import logging
import threading
from collections import deque
import time

import numpy as np

import sensor
import algs
from .domain import Domain
from .fdscommon import RoomConfig, FDSException


class Room(object):
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

    __SENSOR_THREAD_TIMEOUT_SEC: float = 2.0
    __PAUSE_TIMEOUT_SEC: float = 8.0
    __SCAN_MIN_WINDOW_SIZE: int = 5
    __LOW_CLASSIFY_PERIOD_SEC: float = 0.7

    def __init__(self, room_config: RoomConfig, domain_owner: Domain,
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

    def __cond_pauseCheck(self):
        return (self.__threads_to_pause == 0)

    def pauseThreads(self):
        """
        Pause threads in this room.
        """

        if self._activity_state is self.ActivityState.NONE:
            raise FDSException()

        self.__threads_pausing = self.__threads_to_pause
        self.__pause_event.clear()

        if not self.__pause_all_cond.wait_for(self.__cond_pauseCheck,
                                              timeout=self.__PAUSE_TIMEOUT_SEC):
            self.__logger.warn(f"Pausing exceeded timeout of {0} seconds."
                               .format(self.__PAUSE_TIMEOUT_SEC))
        else:
            self.__pause_all_cond.wait_for(self.__cond_pauseCheck,
                                           timeout=None)

        self._activity_state = self.ActivityState.PAUSED
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
            with self.__pause_all_cond:
                self.__threads_pausing -= 1
            self.__pause_all_cond.notify(n=1)
            # Room transitions to PAUSED state, wait for unpause
            self.__pause_event.wait(timeout=None)
            return True
        return False

    def __thread_sensorScanPull(self):
        """
        Thread function.
        Asynchronously copy sensor scans from alternate windows to ensure
        `__thread_sensorScan` is able to produce and store new, up-tod-date
        scans for `__thread_classification` to consume.
        """

        self.__threads_to_pause += 1

        # Wait until the classification thread requests data
        self.__sensor_pull_event.wait(timeout=None)
        while self._sensor_sentinel:
            self.__sensor_pull_event.clear()

            # Copy scans from the alternate windows
            for i in range(0, len(self._lidar_sensors)):
                for scan in self.__lidar_scan_windows_alt[i]:
                    self.__lidar_scan_windows.append(scan)

            # Clear alternate windows - to prevent adding old scans to the
            # main windows
            for i in range(0, len(self._lidar_sensors)):
                self.__lidar_scan_windows_alt[i].clear()

            self.__sensor_pull_event.wait(timeout=None)
        return 0

    def __thread_sensorScan(self):
        """
        Thread function.
        Get sensor scans and data asynchronously and continuously, spawned by
        `__thread_classification()`.
        """

        self.__threads_to_pause += 1

        # Sensor scan thread controls pull thread
        sensor_pull_thread = threading.Thread(
            target=self.__thread_sensorScanPull,
            name="FDS Sensor Data Pull")
        sensor_pull_thread.run()

        # Initialize fixed-length queues
        self.__lidar_scan_windows: List[deque] = []
        self.__lidar_scan_windows_alt = []
        for lidar in self.__lidar_sensors:
            self.__lidar_scan_windows.append(deque(
                iterable=[],
                maxlen=Room._SCAN_MIN_WINDOW_SIZE))
            self.__lidar_scan_windows_alt.append(deque(
                iterable=[],
                maxlen=Room._SCAN_MIN_WINDOW_SIZE))

        # Start the sensors
        for lidar in self.__lidar_sensors:
            lidar.startScanning()

        # Begin sensor sampling/scan loop
        while self._sensor_sentinel:
            # Check for pause event
            if not self.__pause_event.is_set():
                # Room transitions to PAUSED state, wait for unpause
                self.__pause_event.wait(timeout=None)

            # Prevent the thread from pushing scans to the main queues
            # when the classification thread requests data.
            if not self.__sensor_pull_lock.locked():
                # Add to window
                for i in range(0, len(self.__lidar_sensors)):
                    lidar = self.__lidar_sensors[i]
                    self.__lidar_scan_windows[i].append(lidar.getRawData())
            else:
                # Add to temporary windows
                for i in range(0, len(self.__lidar_sensors)):
                    lidar = self.__lidar_sensors[i]
                    self.__lidar_scan_windows_alt[i].append(lidar.getRawData())

        for lidar in self.__lidar_sensors:
            lidar.stopScanning()

        # Ensure pull thread stops
        self.__sensor_pull_event.set()
        sensor_pull_thread.join()
        self._sensor_sentinel = True  # Reset to true for exit
        return 0

    def __pullLidarData(self) -> Iterable[np.ndarray]:
        """
        Pull sensor scans generated by the sensorScan thread.

        :return: An ordered list of raw scans, ordered by increasing degree.
        :rtype: Iterable[np.ndarray]
        """

        sensor_windows = []
        # Freeze the main set of queues...
        self.__sensor_ret_cond = False
        # ...and start copying them.
        for i in range(0, len(self._lidar_sensors)):
            # Copy the lists backing the windows (the deques)
            scan_window = list(self.__lidar_scan_windows[i])
            sensor_windows.append(scan_window)
        # Let the sensorPull thread add scans from the alternate windows
        self.__sensor_pull_event.set()
        # Unfreeze the main set of queues
        self.__sensor_ret_cond = True

        return sensor_windows

    def __classificationProcessLow(self):
        """
        Use a low power/intensity classification algorithm in the LOW activity
        state to find some activity in the room. This algorithm attempts to
        simply cluster the filtered data and find some clusters, with a minimum
        number of points, before switching to the HIGH activity state and
        exiting.
        """

        self._activity_state = self.ActivityState.LOW

        time_tosleep = time.monotonic()

        # Check for occupancy
        lidar_windows = self.__pullLidarData()
        # FUTURE: Process with arbitrary sensors
        lidar_window = lidar_windows[0]
        lidar_window_fil = self.__lidar_sensors[0].filterData(lidar_window)

        (lidar_clusters, _) = \
            self.__lidar_algs.clusterLidarScan(lidar_window_fil)

        while (len(lidar_clusters) == 0):
            # self.__domain._pushData(0, )

            # Checkpoint for pausing
            if not self.__checkPause():
                time_tosleep = self.__LOW_CLASSIFY_PERIOD_SEC - \
                    (time.monotonic() - time_tosleep)
                time.sleep(time_tosleep)

            time_tosleep = time.monotonic()

            lidar_windows = self.__pullLidarData()
            # FUTURE: Process with arbitrary sensors
            lidar_window = lidar_windows[0]
            lidar_window_fil = self.__lidar_sensors[0].filterData(lidar_window)

            (lidar_clusters, _) = \
                self.__lidar_algs.clusterLidarScan(lidar_window_fil)

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
        lidar_windows = self.__pullLidarData()
        # FIXME: Process with arbitrary sensors
        lidar_window = lidar_windows[0]
        lidar_window_fil = self.__lidar_sensors[0].filterData(lidar_window)

        (lidar_clusters, _) = \
            self.__lidar_algs.clusterLidarScanAdv(lidar_window_fil)

        while (len(lidar_clusters) != 0):
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

            # self.__domain._pushData(0, )

            # Checkpoint for pausing
            self.__checkPause()

            lidar_windows = self.__pullLidarData()
            # FIXME: Process with arbitrary sensors
            lidar_window = lidar_windows[0]
            lidar_window_fil = self.__lidar_sensors[0].filterData(lidar_window)

            # Keep checking for occupancy
            (lidar_clusters, _) = \
                self.__lidar_algs.clusterLidarScanAdv(lidar_window_fil)

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
        self.__pause_all_cond = threading.Condition()
        self.__threads_to_pause = 1 # For condition, to check all threads pause
        self.__threads_pausing = 0
        self.__sensor_ret_cond = True
        self.__sensor_pull_event = threading.Event()

        # Room thread controls sensor thread, not the pool
        sensor_thread = threading.Thread(target=self.__thread_sensorScan,
                                         name="FDS Sensor Data Scan Loop")
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
            self.__logger.debug("Sensor thread did not join promptly, exceeded"
                                " {0} seconds"
                                .format(self.__SENSOR_THREAD_TIMEOUT_SEC))
        return 0
