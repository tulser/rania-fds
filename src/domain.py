from typing import Optional, Callable, Any, List

import logging
import threading

import numpy as np

from .fdscommon import DomainConfig
from .sensor import Sensor
from .algs import GlobalTrainingSets, LidarAlgSet
from .room import Room
from .ipc import Socket, FallEventInfo
# FUTURE: Plot should eventually be removed with routines merged into FDSSocket
#   or other status communicator to send plots over a socket
from .plot import LidarPlotter


class Domain(object):
    """
    Class to represent a physical, generic domain such as a house or other
    dwelling. A fall detection system (FDS) is an instance of the class.
    """

    def __init__(self, domain_config: DomainConfig,
                 training: GlobalTrainingSets,
                 sensors: List[Sensor],
                 socket: Socket,
                 logger: logging.Logger):
        """
        :param domain_config: A room specific configuration to use.
        :type domain_config: FDSDomainConfig
        :param socket: A communication interface to communicate with clients.
        :type socket: FDSSocket
        :param logger: The logger to use for logging.
        :type logger: logging.Logger
        """

        self.__config = domain_config
        self.__lidar_alg_set = LidarAlgSet(trainingset=training)
        self.__socket = socket
        self.__logger = logger
        self.__rooms = []
        self.__threads = []
        self.__threads_condexit = threading.Condition()
        self.__threads_toexit = 0

        self.__plotter = LidarPlotter()

        self.addThread(self.__plotter.__thread_plotLoop,
                       name="FDS Plot Loop")
        self.__initalizeRooms(sensors)
        return

    def __initalizeRooms(self, sensors: List[Sensor]):
        """
        Initialize all rooms with given information from the domain
        configuration.
        """

        room_configs = self.__dom_config.room_configs
        logger = self.__logger
        lidar_alg_set = self.__lidar_alg_set
        for room_config in room_configs:
            priv_sensors = []
            for uid in room_config.sensors_assigned:
                priv_sensors.append(sensors[uid])
            self._rooms.append(Room(room_config, self, lidar_alg_set,
                                    priv_sensors, logger))
        return

    def __threadWrapper(self, func: Callable[..., Any]):
        """
        Wrapper for the `addThread` function to wrap threads with counter code
        to ensure the `wait` function unblocks and exits.
        """

        func()
        with self.__threads_condexit:
            self.__threads_toexit -= 1
        self.__threads_condexit.notify(1)
        return

    def addThread(self, target: Callable[..., Any], name: Optional[str] = None,
                  daemon: bool = False):
        """
        Add a thread to the pool before the domain starts it.

        :param target: A function/callable to use as a thread
        :type target: Callable[..., Any]
        :param name: Name for the thread.
        :type name: str
        :param daemon: Indicate if the thread is a daemon thread if True
        :type daemon: bool
        """

        thread = threading.Thread(target=self.__threadWrapper, args=(target),
                                  name=name, daemon=daemon)
        self.__threads_toexit += 1
        self.__threads.append(thread)
        return

    def __runThreads(self):
        """
        Run domain threads in the thread pool.
        Note: This function does not block.
        """

        for thread in self.__threads:
            thread.run()
        return

    def start(self):
        """
        Start execution for the domain. Waits until the threads or the FDS
        exits.
        """

        self.__runThreads()
        self._wait()
        return

    def _wait(self):
        """
        Wait for all threads of the domain to return.
        """

        while self.__threads_toexit != 0:
            self.__threads_condexit.wait(timeout=None)
        return

    def pause(self):
        """
        Pause all processing related to the domain.
        """

        for room in self.__rooms:
            room.pauseThreads()
        return

    def _emitFallEvent(self, room_id):
        """
        Emit a fall event from this instance.
        """

        fe = FallEventInfo(self.__config.id, room_id)
        self.__socket.emitEvent(fe)
        return

    # FUTURE: Remake this to push data over the socket, rather than plot
    def _pushData(self, room_id: int, geometry: np.ndarray, noise: np.ndarray,
                  clusters: List[np.ndarray]):
        """
        Push clusters of samples to clients
        """

        self.__plotter.drawPlot(geometry, noise, clusters)
        return
