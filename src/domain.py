from typing import List, Optional

import logging

import serial.tools.list_ports as list_ports
import numpy as np
from rplidar import RPLidar

from .fdscommon import FDSDomainConfig, FDSException, FDSThreadPool
from .room import FDSRoom


class FDSDomain(object):
    """
    Class to represent a physical, generic domain such as a house or other
    dwelling. A fall detection system (FDS) is an instance of the class.
    """

    def __init__(self, dom_config: FDSDomainConfig, logger: logging.Logger):
        self._dom_config = dom_config
        self._logger = logger
        self._rooms = []
        self._thread_pool = FDSThreadPool()
        self._initalizeRooms()
        self._runRoomThreads()

    def _initalizeRooms(self):
        # TODO: deconstruct domconfig to room tuples
        room_configs = self._dom_config
        for room_config in room_configs:
            self._rooms.append(FDSRoom(room_config, self._thread_pool,
                                       self._logger))

    def _runRoomThreads(self):
        self._thread_pool.runThreads()

    # FIXME: account for changed rplidar dependency (use .sensor module)
    def getValidLidarPorts(ports: Optional[List[str]] = None) -> List[str]:
        """
        Detect and return a list of ports associated with [RP]Lidar devices.

        :return: A list of strings indicating ports.
        """
        if ports is None:
            lidar_ports: List[str] = []
            for port in list_ports.comports():
                if RPLidar(port.device).is_valid_device():
                    lidar_ports.append(port.device)
        else:
            for port in ports:
                if RPLidar(port).is_valid_device():
                    list_ports.append(port)

        return lidar_ports

    def _initializeLidars(self, ids: List[str]):
        pass
