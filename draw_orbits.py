# file to draw the orbits, to visually test physics_simulation.py

import physics_simulation as sim
import matplotlib.pyplot as plt
import matplotlib.animation as animation  
import json
import numpy as np

# radius of solar system (m)
SOLAR_SYSTEM_RAD = 258000000000
# radius near the earth (m)
EARTH_ORBIT_RAD = 485000000
SECONDS_IN_DAY = 86400
# over 1 year in seconds
MAX_T = 31536000

fig, ax = plt.subplots()

ax.set_xlim([-258000000000, 258000000000])
ax.set_ylim([-258000000000, 258000000000]) 

scatter = ax.scatter([], [])

# called for frame i
def animate(i):
    # t is a parameter which varies with the frame number 
    # 2 days per frame
    t =  2 * SECONDS_IN_DAY * i  

    # slow down timer to see moon orbit earth
    t = 360 * i

    x_data = []
    y_data = []
    
    # grab the data from physics_simulation.py
    data = sim.get_stats(t)
    
    for datum in data:       
        # appending values to the previously  
        # empty x and y data holders  
        x_data.append(datum["x"])  
        y_data.append(datum["y"])

    # uncomment to see moon orbit earth
    ax.set_xlim([data[1]["x"] - EARTH_ORBIT_RAD, data[1]["x"] + EARTH_ORBIT_RAD])
    ax.set_ylim([data[1]["y"] - EARTH_ORBIT_RAD, data[1]["y"] + EARTH_ORBIT_RAD]) 

    # add it to animation
    scatter.set_offsets(np.column_stack((x_data, y_data)))  
    return scatter,


# bootstrap for animated python file
def animated():
    anim = animation.FuncAnimation(fig, animate, frames = 500, interval = 20, blit = True)
    # plt.show()

    writergif = animation.PillowWriter(fps=30) 
    anim.save("data/orbit_earth.gif", writer=writergif)


# non animated daily iteration through drawing
def daily_points():
    # get the values of the planets at time t

    t = 0
    colors = ["r", "b", "g", "c", "m", "y"]

    while t < MAX_T:

        data = sim.get_stats(t)
        index = 0

        
        plt.xlim(-SOLAR_SYSTEM_RAD, SOLAR_SYSTEM_RAD)
        plt.ylim(-SOLAR_SYSTEM_RAD, SOLAR_SYSTEM_RAD)
        
        for datam in data:
            index = (index + 1) % len(colors)
            plt.plot(datam["x"], datam["y"], colors[index] + 'o')
            

        t += SECONDS_IN_DAY
        plt.show()
    

animated()
