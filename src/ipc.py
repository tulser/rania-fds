from typing import override
from abc import abstractmethod

from threading import Thread
from os.path import realpath
import logging
import json

import zmq


class EventInfo(object):
    """
    Abstract class for events emitted by the fall detection system.
    """

    def __init__(self, domain_id):
        self._domain_id = domain_id
        return

    @property.getter
    @abstractmethod
    def dict(self) -> dict:
        raise NotImplementedError


class FallEventInfo(EventInfo):
    def __init__(self, domain_id, room_id):
        super().__init__(domain_id)
        self._room_id = room_id
        return

    @override
    @property.getter
    def dict(self) -> dict:
        return


class Socket(object):
    """
    Class for managing connectiosn from the FDS to potentially multiple
    sources.
    """

    __SOCKET_PREFIX = "fds"

    def __init__(self, socket_dir: str, logger: logging.Logger):
        socket_path_rep = None
        socket_path_pub = None
        try:
            socket_path_rep = \
                realpath(socket_dir + self.__SOCKET_PREFIX + "-rep")
            socket_path_pub = \
                realpath(socket_dir + self.__SOCKET_PREFIX + "-pub")
        except Exception as err:
            raise err

        zmq_ctxt = zmq.Context()
        self.__socket_paths = (socket_path_rep, socket_path_pub)
        self.__cmd_socket = zmq_ctxt.socket(zmq.REP)
        self.__pub_socket = zmq_ctxt.socket(zmq.PUB)
        self.__zmq_ctxt = zmq_ctxt

        self.__listener_thread = Thread(target=self.__thread_cmdlistener,
                                        name="FDS Socket Command Listener")

        self._sockets_bound = False

        self.__logger = logger
        return

    def bindBegin(self):
        self._sockets_bound = True
        self._startListener()
        self._startPublisher()
        return

    def _startListener(self):
        self.__cmd_socket.bind("ipc://" + self.__socket_paths[0])
        self.__listener_thread.run()
        return

    def _startPublisher(self):
        self.__pub_socket.bind("ipc://" + self.__socket_paths[1])
        return

    def __thread_cmdlistener(self):
        while True:
            pkt = self.__cmd_socket.recv()

            self.__cmd_socket.send(something)

    def emitEvent(self, event: EventInfo):
        jdump = json.dumps(event.dict)
        self.__pub_socket.send(bytes(jdump, encoding="utf-8"))
        return
