from typing import Optional
from enum import Enum

import logging
from os.path import realpath
import io
import sys
import socket
import pickle

from .fdscommon import FDSGlobalConfig, FDSException
from .domain import FDSDomain


class FDSLogLevel(Enum):
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class FDSLogFilter(logging.Filter):
    def __init__(self, logpath: Optional[str] = None):
        self.logpath = logpath

    def filter(record: logging.LogRecord):
        if record.level <= logging.WARNING:
            sys.stdout.write(record.msg)
        else:
            sys.stderr.write(record.msg)


# Use for testing
DEFAULT_CONFIG_PATH_POSIX = "/etc/rania-fds/fds.conf"

# FDS instance global variables
logger: logging.Logger = None

fds_config: FDSGlobalConfig() = None
fsocket: socket.socket = None
fsocket_conns = None


def main(config_path: Optional[str] = None,
         loglevel: FDSLogLevel = FDSLogLevel.INFO):
    # TODO: implement config parsing and processing
    global logger
    global fds_config
    logger = logging.Logger("rania-fds", loglevel)
    logger.addFilter(FDSLogFilter())

    if config_path is None:
        # TODO: Refactor to check multiple paths
        #       (for different systems/distributions)
        fds_config = _getFDSConfig(DEFAULT_CONFIG_PATH_POSIX)
    else:
        fds_config = _getFDSConfig(config_path)

    _initSocket(fds_config.sock_path)

    domain = FDSDomain(fds_config.dom_config, socket)
    domain.start()
    return


def _initSocket(sock_path: str):
    global logger
    global fsocket

    try:
        sock_path = realpath(sock_path)
    except Exception as err:
        raise err

    fsocket = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
    fsocket.bind(sock_path)
    # TODO: Create a thread to listen for socket connections
    return


def _socketHandler():
    pass


def _deinitSocket():
    global logger
    global fsocket


def _getFDSConfig(config_path: str) -> FDSGlobalConfig:
    global logger
    try:
        config_path = realpath(config_path)
    except Exception as err:
        logger.log(logging.ERROR,
                   (f"Cannot open config file at path "
                    f"\"{config_path}\": {err}"))
        raise err

    try:
        fds_file = io.open(config_path, 'rb')
    except Exception as err:
        raise err
    else:
        with fds_file:
            # TODO: Parse fds config
            # NOTE: For this implementation, we assume there is one domain that
            #       is equivalent to the FDS, i.e, a domain represents an FDS
            return FDSGlobalConfig()


if __name__ == "__main__":
    main()
