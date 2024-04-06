from typing import override

from threading import Thread, Semaphore
from os.path import realpath
import socket
import logging
import json


class FDSEvent:
    def __init__(self, domain_id):
        self._domain_id = domain_id
        return

    @property.getter
    def dict(self):
        raise NotImplementedError


class FDSFallEvent(FDSEvent):
    def __init__(self, domain_id, room_id):
        super().__init__(domain_id)
        self._room_id = room_id
        return

    @override
    @property.getter
    def dict(self):
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

        self._sock_path = sock_path
        self.__srv_socket = socket.socket(family=socket.AF_UNIX,
                                          type=socket.SOCK_STREAM)
        # Multiple threads can access `__cl_conn_list`
        self.__cl_conn_list_mtx = Semaphore()
        self.__cl_conn_list = []

        self._listener_thread = Thread(target=self.__connListenThread,
                                       name="FDS Socket Connection Listener")

        self._logger = logger
        return

    def startListener(self):
        self._listener_thread.run()

    def __connCtlThread(self, conn: socket):

        # Terminate the connection
        with self.__cl_conn_list_mtx:
            self.__cl_conn_list.remove(conn)
        conn.close()
        return

    def __connListenThread(self):
        # Bind the socket
        self.__srv_socket.bind(self._sock_path)
        self.__srv_socket.listen()
        # Enter wait loop for accepting new socket connections
        while True:
            (new_conn, _) = self._srv_socket.accept()
            new_conn_th = Thread(target=self.__connCtlThread,
                                 args=new_conn,
                                 name="FDS Client Listener")
            with self.__cl_conn_list_mtx:
                self.__cl_conn_list.append(new_conn)
            new_conn_th.run()

    def emitEvent(self, event: FDSEvent):
        jdump = json.dumps(event.dict)
        with self.__cl_conn_list_mtx:
            for conn in self.__cl_conn_list:
                s = conn.sendall(bytes(jdump, encoding="utf-8"))
        return
