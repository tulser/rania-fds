import fds.main


def main():
    fds.main()
    return
'''
    lidar_port = getLidarPort()
    lidar = RPLidar(lidar_port)
    iterator = lidar.iter_scans()
    old_scan = getNewScan(iterator)
    old_labels = clusterScan(old_scan)
    old_clusters = separateClusters(old_scan, old_labels)

    new_scan = getNewScan(iterator)
    new_labels = clusterScan(new_scan)
    new_clusters = separateClusters(new_scan, new_labels)

    updated_clusters = checkClosestClusters(new_clusters, old_clusters)

    # print(new_clusters)

    sendScanToServer(updated_clusters)
    # print(hausdorffDistanceFast(old_clusters[1], new_clusters[2]))

    # print(old_clusters)
    while(True):
        old_clusters = new_clusters
        new_scan = getNewScan(iterator)
        new_labels = clusterScan(new_scan)
        new_clusters = separateClusters(new_scan, new_labels)
        # print(new_clusters)

        updated_clusters = checkClosestClusters(new_clusters, old_clusters)
        # print(updated_clusters[0])
        sendScanToServer(updated_clusters)

        # new_scan = getNewScan(iterator)
        # labels = clusterScan(new_scan)
        # result = [scan_tuple + (label,)
        #           for scan_tuple, label in zip(new_scan, labels)]
        # # Extract x and y values from the data
        # # print(new_scan)
        # sendScanToServer(result)
'''

if __name__ == "__main__":
    main()
