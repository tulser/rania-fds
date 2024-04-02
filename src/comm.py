
from threading import Thread
from os.path import realpath
import socket
import logging


class FDSEvent:
    def __init__(self):
        self._domain_id = 0
        return


class FDSFallEvent(FDSEvent):
    def __init__(self, room_id):
        self._room_id = room_id
        return


class FDSSocket(object):
    """
    Class for managing a global socket connection from the FDS to potentially
    multiple sources
    """

    def __init__(self, sock_path: str, logger: logging.Logger):
        try:
            sock_path = realpath(sock_path)
        except Exception as err:
            raise err

        socket_handle = socket.socket(family=socket.AF_UNIX,
                                      type=socket.SOCK_STREAM)
        socket_handle.bind(sock_path)
        # TODO: Create a thread to listen for socket connections

        self._socket_handle = socket_handle
        self._listener_thread = Thread(target=self.__listenerThreadProc,
                                       name="FDS Socket Listener")

        return self

    def startListener(self):
        self._listener_thread.run()

    def __listenerThreadProc(self):
        pass

    def emitEvent(self, FDSEvent):
        pass

    def sendMessage(self):
        pass

    def recvMessageHandler(self):  # callback
        pass


def _socketHandler():
    pass


def _deinit():
    global logger
    global fsocket
