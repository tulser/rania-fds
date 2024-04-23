import pickle
import argparse

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import numpy as np

from src.base_config import basicConfig
from src.sensor import RPLidar, BoundsCalibrationData
from src.util import convertPolarCartesian


DEFAULT_SECTORS = 36
SCANS_MAX = 20
DBS_EPS = 0.5
DBS_MIN_SAMP = 6


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sensor", type=int, nargs=1, action="store")
    parser.add_argument("--sectors", "-s", type=int, nargs="?",
                        action="store_const", const=DEFAULT_SECTORS)
    parser.add_argument("--configpath", "-c", type=str, nargs="?",
                        action="store_const", const=None)

    args = parser.parse_args()

    # TODO: Use arguments
    sensorid = 0  # Not used currently
    sectors = args.sectors
    # configpath = args.config  # Not used currently

    interval_size = 360.0 / sectors

    # Initialize sensor
    config = basicConfig()
    sensor = RPLidar(config.sensors[sensorid], None)
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
    ss = StandardScaler()
    scan_all_cart_norm = ss.fit_predict(scan_all_cart)
    dbs = DBSCAN(eps=DBS_EPS, min_samples=DBS_MIN_SAMP, metric="euclidean")
    labels = dbs.fit_predict(scan_all_cart_norm)
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
    for i in range(0, sectors):
        interval_end = interval_size * (i + 1)
        while scan_final[ns][0] < interval_end:
            ns += 1
        sample_slice = scan_final[bs:ns]
        bound = np.min(sample_slice, axis=0)[1]
        bounds.append([interval_end, bound])
        bs = ns
    bounds_np = np.array(bounds)
    calib_data = BoundsCalibrationData(arcsec_bounds=bounds_np)

    # Save the calibration
    with open(config.sensors[sensorid].calibration_path, "wb") as file:
        pickle.dump(calib_data, file)

    return


if __name__ == "__main__":
    main()
