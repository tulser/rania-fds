from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import math
import numpy as np
from rplidar import RPLidar
import matplotlib.pyplot as plt

PI = math.pi
TAU = 2*PI

def getAngDiff(x,y):
    a = (x-y) % TAU
    b = (y-x) % TAU
    return -a if a<b else b

def getNewScan(iterator):
     scan = next(iterator)
     scan_no_first_value = [(x,y) for _,x,y in scan]
     return scan_no_first_value

def clusterScan(scan):
    data_array = np.array(scan)
    data_normalized = StandardScaler().fit_transform(data_array)
    dbscan = DBSCAN(eps=0.5, min_samples=3)
    labels = dbscan.fit_predict(data_normalized)
    return labels

def plot(x,y):
     plt.figure(figsize=(8, 6))
     plt.scatter(x, y, c='blue', s=10)  
     plt.xlabel('X (mm)')
     plt.ylabel('Y (mm)')
     plt.title('LiDAR Scan')
     plt.grid(True)
     plt.axis('equal')  # Set aspect ratio to equal for square plot
     plt.show()
     


lidar = RPLidar('COM3', baudrate=115200)
info = lidar.get_info()
print(info)

ang = 0
dist = 5000
viewAngle = 180
rangeLimit = 6000
depthLimit = 10
dispWidth = 1920 / 2

spotAng = []
spotDist = []
spotNumber = []
counter = 0


for i, scan in enumerate(lidar.iter_scans(min_len=5, max_buf_meas=False)):
     group = 0
     spotAng = []
     spotX = []
     spotY = []
     spotDist = []
     spotNumber = []

     for x in range(len(scan)):
         

               if scan[x][2] < rangeLimit:
                    #point is within scanning distance
                    ang = scan[x][1]
                    dist = scan[x][2]
                    if len(spotAng) -1 != group:
                         #first point detected, add to first array
                         spotAng.append(ang)
                         spotDist.append(dist)
                         spotNumber.append(1)
                         calcAng = round(ang-270)
                         x = math.cos(math.radians(calcAng)) * dist
                         y = math.sin(math.radians(calcAng)) * dist
                         spotX.append(x)
                         spotY.append(y)

                    else:
                         #still in the same group, check for angle
                         angDiff = getAngDiff(ang, spotAng[group])

                         if angDiff < 40: #if difference is less than x degrees
                              if abs(dist - spotDist[group]) < 3:
                                   #if distance is also within same area
                                   spotAng[group] = ang
                                   spotNumber[group] += 1
                                   spotDist[group] = dist
                                   calcAng = round(ang-270)
                                   x = math.cos(math.radians(calcAng)) * dist
                                   y = math.sin(math.radians(calcAng)) * dist
                                   spotX[group] += x
                                   spotY[group] += y

                              else:
                                   group += 1

                         else:
                         #out of bounds
                              group += 1

     for spots in range(len(spotNumber)):
          spotX[spots] = round(spotX[spots] / spotNumber[spots])
          spotY[spots] = round(spotY[spots] / spotNumber[spots])
     if (len(spotAng) > 0):
        
          counter += 1
          if counter == 11:
               coordinate_pairs = list(zip(spotX, spotY))
               lidar_data = clusterScan(coordinate_pairs)
               print(coordinate_pairs)
               print(lidar_data)
               #filtered_points = coordinate_pairs[lidar_data == 0]
               #x_filtered = filtered_points[:, 0]
               #y_filtered = filtered_points[:, 1]
               #plot(x_filtered, y_filtered)
               plot(spotX, spotY)
              
               lidar.stop()
               lidar.stop_motor()
               lidar.disconnect()
               quit()







