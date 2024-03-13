# file to draw the orbits, to visually test physics_simulation.py

import physics_simulation as sim
import matplotlib.pyplot as plt
import matplotlib.animation as animation  
import json
import numpy as np


fig, ax = plt.subplots()

# ax.set_xlim([-258000000000, 258000000000])
# ax.set_ylim([-258000000000, 258000000000]) 

scatter = ax.scatter([], [])


def animate(i):
    # t is a parameter which varies 
    # with the frame number 
    t =  2 * 86400 * i  

    # slow down timer to see moon orbit earth
    # t = 3600 * i

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
    # ax.set_xlim([data[1]["x"] - 485000000, data[1]["x"] + 485000000])
    # ax.set_ylim([data[1]["y"] - 485000000, data[1]["y"] + 485000000]) 

    # add it to animation
    scatter.set_offsets(np.column_stack((x_data, y_data)))  
    return scatter,


# bootstrap for animated python file
def animated():
    anim = animation.FuncAnimation(fig, animate, frames = 5000, interval = 20, blit = True)
    plt.show()


# non animated daily iteration through drawing
def daily_points():
    # get the values of the planets at time t

    t = 0
    colors = ["r", "b", "g", "c", "m", "y"]

    while t < 31536000:

        data = sim.get_stats(t)
        index = 0

        plt.xlim(-258000000000, 258000000000)
        plt.ylim(-258000000000, 258000000000)
        
        for datam in data:
            index = (index + 1) % len(colors)
            plt.plot(datam["x"], datam["y"], colors[index] + 'o')
            

        t += 86400
        plt.show()
    

animated()
