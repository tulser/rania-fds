from typing import List, Optional

import logging

import serial.tools.list_ports as list_ports

from .sensor import RPLidar
from .fdscommon import FDSDomainConfig, FDSThreadPool, FDSException
from .room import FDSRoom
from .comm import FDSSocket, FDSFallEvent


class FDSDomain(object):
    """
    Class to represent a physical, generic domain such as a house or other
    dwelling. A fall detection system (FDS) is an instance of the class.
    """

    def __init__(self, dom_config: FDSDomainConfig, socket: FDSSocket,
                 logger: logging.Logger):
        self._dom_config = dom_config
        self.__socket = socket
        self._logger = logger
        self._rooms = []
        self._thread_pool = FDSThreadPool()
        self.__initalizeRooms()

    def __initalizeRooms(self):
        room_configs = self._dom_config.room_configs
        for room_config in room_configs:
            self._rooms.append(FDSRoom(room_config, self._thread_pool,
                                       self._logger))

    def _roomEmitFallEvent(self, room_id):
        fe = FDSFallEvent(0, room_id)
        self.__socket.emitEvent(fe)
        return

    def start(self):
        return self._runThreads()

    def _runThreads(self):
        self._thread_pool.runThreads()

    def getValidLidarPorts(ports: Optional[List[str]] = None) -> List[str]:
        """
        Detect and return a list of ports associated with [RP]Lidar devices.

        :return: A list of strings indicating ports.
        """
        if ports is None:
            lidar_ports: List[str] = []
            for port in list_ports.comports():
                if RPLidar.is_valid_device(port.device):
                    lidar_ports.append(port.device)
        else:
            for port in ports:
                if RPLidar.is_valid_device(port):
                    list_ports.append(port)

        return lidar_ports
