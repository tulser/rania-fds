from typing import (List, Iterable)

from enum import Enum
import logging
import threading
from collections import deque

import numpy as np
from rplidar import RPLidar

from .fdscommon import (FDSRoomConfig, FDSThreadPool, FDSThreadType,
                        FDSException)


class FDSRoom(object):
    '''
    Class representing a room/spacial unit of an FDSDomain
    '''

    class ActivityState(Enum):
        NONE = 0
        LOW = 1
        HIGH = 2

    _SCAN_MIN_WINDOW_SIZE = 5

    def __init__(self, room_config: FDSRoomConfig, thread_pool: FDSThreadPool,
                 logger: logging.Logger):
        self._roomconfig = room_config
        self._thread_pool = thread_pool
        self._logger = logger
        self._scans = np.ndarray(self._WINDOW_SIZE)
        # Sema4 value ensures roomThread does not immediately begin processing
        # before the full scan window completes at the first loop.
        self._sensor_mutex = threading.Semaphore(value=0)

        self._threadpool.addThread(target=self._roomThread)

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

    def _updateWindow(self, iterator, window):
        window = window[1:] + self._getNewScan(iterator)

    def _sensorThread(self):
        self._lidar_iterators: List[Iterable] = []
        self._scan_windows: List[deque] = []
        for lidar in self._lidars:
            lidar.start()
            iterator = lidar.iter_scans(min_len=FDSRoom._SCAN_MIN_WINDOW_SIZE)
            self._scan_iterators.append(iterator)
            self._scan_windows.append(deque(
                iterable=[],
                maxlen=FDSRoom._SCAN_MIN_WINDOW_SIZE))

        lidars_size: int = len(self._lidars)
        while self._sensor_sentinel:
            # TODO: Use mutex to pause thread
            # Add to window
            for i in range(0, lidars_size):
                iter = self._lidar_iterators[i]
                scan = next(iter)
                scan_fv = [(deg, dist) for _, deg, dist in scan]
                self._scan_windows[i].append(scan_fv)

        for lidar in self._lidars:
            lidar.stop()

        self._sensor_sentinel = True  # confirm for exit
        return 0

    def __roomThread_lowProcess(self):
        while True:
            # TODO: Use mutex to pause thread
            if True:  # pseduo code
                self._activity_state = FDSRoom.ActivityState.HIGH
                self.__roomThread_stateProcess = self.__roomThread_highProcess
            break
        return

    def __roomThread_highProcess(self):
        pass

    def _roomThread(self):
        # function to run in its own thread for real-time processing
        # room thread controls sensor thread
        sensor_thread = threading.Thread(target=self._sensorThread)
        self._sensor_sentinel = True
        sensor_thread.run()
        # begin fall detection processing loop
        self.__roomThread_stateProcess = self.__roomThread_lowProcess
        while True:
            try:
                exit_status = self.__roomThread_stateProcess()
                if exit_status == 0:
                    break
            except FDSException as err:
                raise err

        self._sensor_sentinel = False
        sensor_thread.join(2.0)
        
        return 0
