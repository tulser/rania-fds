from typing import Dict, Callable, Any

from threading import Thread
from os.path import exists
import logging
import json

import zmq


class EventInfo(dict):
    """
    Abstract class for events emitted by the fall detection system.
    """

    def __init__(self, domain_id: int):
        super().__init__(self)
        self["dom_id"] = domain_id
        return


class FallEventInfo(EventInfo):

    def __init__(self, domain_id: int, room_id: int):
        super().__init__(domain_id)
        self["type"] = "fall_start"
        self["data"] = {}
        self["data"]["room_id"] = room_id
        return


class CommandInfo(dict):

    def getCmdType(self) -> int:
        return self["type"]

    def getCmdData(self) -> dict:
        return self["data"]


class FDSSocketPathError(Exception):
    pass


class Socket(object):
    """
    Class for managing connectiosn from the FDS to potentially multiple
    sources.
    """

    __SOCKET_PREFIX = "fds"

    def __init__(self, socket_dir: str,
                 post_num: int,
                 callbacks: Dict[int, Callable[[dict], Any]],
                 logger: logging.Logger):
        socket_path_rep = socket_dir + self.__SOCKET_PREFIX + post_num + "-rep"
        socket_path_pub = socket_dir + self.__SOCKET_PREFIX + post_num + "-pub"

        if exists(socket_path_rep) or exists(socket_path_pub):
            raise FDSSocketPathError()

        zmq_ctxt = zmq.Context()
        self.__socket_paths = (socket_path_rep, socket_path_pub)
        self.__cmd_socket = zmq_ctxt.socket(zmq.REP)
        self.__pub_socket = zmq_ctxt.socket(zmq.PUB)
        self.__zmq_ctxt = zmq_ctxt

        self.__listener_thread = Thread(target=self.__thread_cmdListener,
                                        name="FDS Socket Command Listener")

        self._sockets_bound = False
        self.__callback_dict = callbacks

        self.__logger = logger
        return

    def bindBegin(self):
        self._startListener()
        self._startPublisher()
        self._sockets_bound = True
        return

    def _startListener(self):
        self.__cmd_socket.bind("ipc://" + self.__socket_paths[0])
        self.__listener_thread.run()
        return

    def _startPublisher(self):
        self.__pub_socket.bind("ipc://" + self.__socket_paths[1])
        return

    def __thread_cmdListener(self):
        cmd_socket = self.__cmd_socket
        while True:
            pkt = cmd_socket.recv()
            try:
                ci = CommandInfo(json.loads(pkt))
            except json.JSONDecodeError:
                self.__logger.warn("Could not decode command packet.")
                continue

            ci_type = ci.getCmdType()
            if ci_type not in self.__callback_dict:
                self.__logger.warn(f"Command with id `{0}` not recognized."
                                   .format(ci_type))
                continue
            res = self.__callback_dict[ci_type](ci.getCmdData())

            # Send result back to the commanding client
            # With ZMQ, this step is preferred in case there is a need to
            #   address the sending client (which sent the command).
            # TODO: Send callback results instead of constant
            cmd_socket.send(json.dumps(0))
        return

    def emitEvent(self, event: EventInfo):
        jdump = json.dumps(event)
        self.__pub_socket.send(bytes(jdump, encoding="utf-8"))
        return
