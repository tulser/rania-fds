from typing import (List, Iterable)

from enum import Enum
import logging
import threading
from collections import deque

import numpy as np

import sensor
from fdscommon import (FDSRoomConfig, FDSThreadPool, FDSThreadType,
                       FDSException)


class FDSRoom(object):
    """
    Class representing a room/spacial unit of an FDSDomain
    """

    class ActivityState(Enum):
        NONE = 0
        LOW = 1
        HIGH = 2

    _SENSOR_THREAD_TIMEOUT = 2.0
    _SCAN_MIN_WINDOW_SIZE = 5

    def __init__(self, room_config: FDSRoomConfig, thread_pool: FDSThreadPool,
                 logger: logging.Logger):
        self._roomconfig = room_config
        self._thread_pool = thread_pool
        self._logger = logger
        self._scans = np.ndarray(self._WINDOW_SIZE)
        self._sensors = sensor.getSensors(room_config, logger)
        # control over starting the room is managed by the owning domain
        self._threadpool.addThread(target=self.__thread_classification)

    def _getNewScan(iterator):
        scan = next(iterator)
        scan_no_first_value = [(x, y) for _, x, y in scan]
        return scan_no_first_value

    def _generateInitialWindow(self, iterator, window_size):
        window = []
        for i in range(0, window_size):
            print(self._getNewScan(iterator))
            # window.append(getNewScan(iterator))
        return window

    def __thread_sensordata(self):
        """
        Get sensor scans and data asynchronously and continuously, spawned by
        `__thread_classification()`.
        """
        self._lidar_iterators: List[Iterable] = []
        self._scans: List[deque] = []
        for lidar in self._lidars:
            lidar.start()
            iterator = lidar.iter_scans(min_len=FDSRoom._SCAN_MIN_WINDOW_SIZE)
            self._scan_iterators.append(iterator)
            self._scans.append(deque(
                iterable=[],
                maxlen=FDSRoom._SCAN_MIN_WINDOW_SIZE))

        lidars_size: int = len(self._lidars)
        while self._sensor_sentinel:
            # TODO: pause thread
            # Add to window
            for i in range(0, lidars_size):
                iter = self._lidar_iterators[i]
                scan = next(iter)
                scan_fv = [(deg, dist) for _, deg, dist in scan]
                self._scans[i].append(scan_fv)

        for lidar in self._lidars:
            lidar.stop()

        self._sensor_sentinel = True  # confirm for exit
        return 0

    def __classificationProcessLow(self):
        while True:
            # TODO: Use mutex to pause thread
            if True:
                self._activity_state = FDSRoom.ActivityState.HIGH
                self.__classificationProcess = self.__classificationProcessHigh
            break
        return

    def __classificationProcessHigh(self):
        pass

    def __thread_classification(self):
        """
        Process data from sensor scans, spawned and started by thread pool.
        """
        # function to run in its own thread for real-time processing
        # room thread controls sensor thread
        sensor_thread = threading.Thread(target=self._sensorThread)
        self._sensor_sentinel = True
        sensor_thread.run()
        # begin fall detection processing loop
        self._activity_state = FDSRoom.ActivityState.LOW
        self.__classificationProcess = self.__classificationProcessLow
        while True:
            try:
                exit_status = self.__classificationProcess()
                if (exit_status == 0):
                    break
            except FDSException as err:
                raise err

        self._sensor_sentinel = False
        sensor_thread.join(FDSRoom._SENSOR_THREAD_TIMEOUT)
        if (not self._sensor_sentinel):
            self._logger.debug("Sensor thread did not join promptly, exceeded "
                               "{0} seconds" % FDSRoom._SENSOR_THREAD_TIMEOUT)
        return 0
