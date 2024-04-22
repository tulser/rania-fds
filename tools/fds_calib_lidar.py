import pickle

from sklearn.cluster import DBSCAN
import numpy as np

from ..src.base_config import basicConfig
from ..src.sensor import RPLidar, BoundsCalibrationData
from ..src.util import convertPolarCartesian


SCANS_MAX = 20
DEFAULT_INTERVALS = 36
DEFAULT_INTERVAL_SPAN = 360 / DEFAULT_INTERVALS
DBS_EPS = 1
DBS_MIN_SAMP = 5


def main():
    # FUTURE: Parse sensor/room arguments and configuration, interval size(?)

    # Initialize sensor
    config = basicConfig()
    sensor = RPLidar(config.sensors[0], None)  # Using specific sensor 0
    sensor.startScanning()

    # Get scans of the environment
    scan_list = []
    for i in range(0, SCANS_MAX):
        scan_list.append(sensor.getRawSamples())
    # Merge scans into one set
    scan_all = np.concatenate(scan_list, axis=0)
    # The array is sorted to make bounds calculation easier
    scan_all = np.sort(scan_all, axis=0)

    # Use single set to remove noise
    scan_all_cart = convertPolarCartesian(scan_all)
    dbs = DBSCAN(eps=DBS_EPS, min_samples=DBS_MIN_SAMP, metric="euclidean")
    labels = dbs.fit_predict(scan_all_cart)
    scan_all_fil = []
    for sample, label in zip(scan_all, labels):
        if (label != -1):
            scan_all_fil.append(sample)
    # Final scan with noise culled
    scan_final = np.array(scan_all_fil)

    # Calculate bounds
    bounds = []
    bs = 0
    ns = 0
    for i in range(0, DEFAULT_INTERVALS):
        interval_end = DEFAULT_INTERVAL_SPAN * (i + 1)
        while scan_final[ns][0] < interval_end:
            ns += 1
        sample_slice = scan_final[bs:ns]
        bound = np.min(sample_slice, axis=0)[1]
        bounds.append([interval_end, bound])
        bs = ns
    bounds_np = np.array(bounds)
    calib_data = BoundsCalibrationData(arcsec_bounds=bounds_np)

    with open(config.sensors[0].calibration_path, "wb") as file:
        pickle.dump(calib_data, file)
    return


if __name__ == "__main__":
    main()
