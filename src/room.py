import logging
import threading

import numpy as np
from rplidar import RPLidar

from .fdscommon import (FDSRoomConfig, FDSThreadPool, FDSThreadType,
                        FDSException)


class FDSRoom(object):
    '''
    Class representing a room/spacial unit of an FDSDomain
    '''

    _WINDOW_SIZE = 5

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

    # TODO: Implement sensor data acquisition thread/loop, room process states
    def _sensorThread(self):
        pass

    def _roomThread_LowStateProcess(self):
        pass

    def _roomThread_HighStateProcess(self):
        pass

    def _roomThread(self):
        # function to run in its own thread for real-time processing
        # room thread controls sensor thread
        sensor_thread = threading.Thread(target=self._sensorThread)
        sensor_thread.run()
        # begin fall detection processing loop
        while True:
            with self._sensor_mutex:
                # TODO: Implement processing
                break
        return
