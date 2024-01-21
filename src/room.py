from rplidar import RPLidar
import numpy as np


class FDSRoom(object):
    '''
    Class representing a room/spacial unit of an FDSDomain
    '''

    _WINDOW_SIZE = 5

    def __init__(self):
        self.scans = np.ndarray(self._WINDOW_SIZE)

    def getNewScan(iterator):
        scan = next(iterator)
        scan_no_first_value = [(x, y) for _, x, y in scan]
        return scan_no_first_value

    def generateInitialWindow(self, iterator, window_size):
        window = []
        for i in range(0, window_size):
            print(self.getNewScan(iterator))
            # window.append(getNewScan(iterator))
        return window

    def updateWindow(self, iterator, window):
        window = window[1:] + self.getNewScan(iterator)

    def roomThread():
        # function to run in its own thread for real-time processing
        pass
