from typing import List
from dataclasses import dataclass

import threading

from sensor import SensorInfo


class FDSException(Exception):
    pass


@dataclass
class FDSRoomConfig:
    assigned_sensors: List[SensorInfo]


@dataclass
class FDSDomainConfig:
    room_configs: List[FDSRoomConfig]


@dataclass
class FDSGlobalConfig:
    socket_path: str
    dom_config: FDSDomainConfig


class FDSRoomThreadPool(object):
    """
    Class mastered by FDSDomains and used by FDSRooms to add and start room
    threads. Allows room threads of a domain to be monitored.
    """

    def __init__(self):
        self._threads = []
        return

    def addThread(self, target):
        thread = threading.Thread(target=target)
        self._threads.append(thread)

    def runThreads(self):
        for thread in self._threads:
            thread.run()
