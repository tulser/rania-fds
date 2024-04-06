from typing import Optional
from enum import Enum

from os.sys import realpath
import logging
import io
import sys
import pickle

from fdscommon import FDSGlobalConfig, FDSException
from domain import FDSDomain
import comm


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


def _getFDSConfig(config_path: str, logger: logging.Logger) -> FDSGlobalConfig:
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


def _getDefaultFDSConfig() -> FDSGlobalConfig:
    pass


def main(config_path: Optional[str] = None,
         loglevel: FDSLogLevel = FDSLogLevel.INFO):
    logger = logging.Logger("rania-fds", loglevel)
    logger.addFilter(FDSLogFilter())

    fds_config = _getDefaultFDSConfig()

    # TODO: Get and parse config from filesystem, potentially to overwrite
    #       aspects of the default config.
    # if config_path is None:
    #     # TODO: Refactor to check multiple paths (for different systems/
    #     #       distributions) or rework for a database
    #     fds_config = _getFDSConfig(DEFAULT_CONFIG_PATH_POSIX)
    # else:
    #     fds_config = _getFDSConfig(config_path)

    socket_master = comm.FDSSocket(fds_config.sock_path, logger)

    domain = FDSDomain(fds_config.dom_config, socket_master, logger)
    domain.start()
    return


if __name__ == "__main__":
    main()
