from typing import List, Optional
import serial.tools.list_ports as list_ports
import numpy as np

from .room import FDSRoom
from rplidar import RPLidar


class FDSDomain(object):
    """
    Class to represent a physical, generic domain such as a house or other
    dwelling. A fall detection system (FDS) is an instance of the class.
    """

    def __init__(self):
        self._initalizeRooms()
        self.runFDS()

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

    def _retrieveRoomInfo() -> np.ndarray:
        """
        Get room data from the database or configuration
        """
        pass

    def _initializeRooms(self):
        roominfo = self._retrieveRoomInfo()
        pass

    def runFDS(self):
        # run room threads
        #for room in self._rooms:
        #   run
        pass
