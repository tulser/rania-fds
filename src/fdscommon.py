from typing import List
from dataclasses import dataclass

import threading


class FDSException(Exception):
    pass


@dataclass
class FDSRoomConfig:
    pass


@dataclass
class FDSDomainConfig:
    room_configs: List[FDSRoomConfig]


@dataclass
class FDSGlobalConfig:
    socket_path: str
    dom_config: FDSDomainConfig


class FDSRoomThreadPool(object):

    def __init__(self):
        self._threads = []
        return

    def addThread(self, target):
        thread = threading.Thread(target=target)
        self._threads.append(thread)

    def runThreads(self):
        for thread in self._threads:
            thread.run()
