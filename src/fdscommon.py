from typing import (List, Tuple)
from dataclasses import dataclass

import threading

import numpy as np

from .sensor import SensorInfo


class FDSException(Exception):
    pass


@dataclass
class FDSRoomConfig:
    sensors_asid: List[str]


@dataclass
class FDSDomainConfig:
    room_configs: List[FDSRoomConfig]


@dataclass
class FDSGlobalConfig:
    socket_path: str
    sensors: List[SensorInfo]
    dom_config: FDSDomainConfig


@dataclass
class FDSGlobalTrainingSet:
    lidar_training: Tuple[np.ndarray, np.ndarray]


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
