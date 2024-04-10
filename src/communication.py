import configparser
from comm import FDSSocket
from domain import FDSDomain
from fdscommon import FDSDomainConfig, FDSRoomConfig, FDSGlobalConfig, FDSRoomThreadPool

config = configparser.ConfigParser()
config.read('config.ini')
