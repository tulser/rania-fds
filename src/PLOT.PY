import matplotlib.pyplot as plt

def plot(x,y):
     plt.figure(figsize=(8, 6))

     colors = []
     for xi,yi in zip(x,y):
          if -800<=xi <= 1000 and -2000 <=yi<=-500:
               colors.append('red')
          else:
               colors.append('blue')

        
     plt.scatter(x, y, c=colors, s=10)  # Customize color and size as needed
     plt.xlabel('X (mm)')
     plt.ylabel('Y (mm)')
     plt.title('LiDAR Scan')
     plt.grid(True)
     plt.axis('equal')  # Set aspect ratio to equal for square plot
     plt.show()

data = []
x = [coord[0] for coord in data]
y = [coord[1] for coord in data]

plot(x,y)