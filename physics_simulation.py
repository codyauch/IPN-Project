import math
import json

# Speed of light m/s
C = 299792458.0

# Transmission Frequency (Hz)
T_FREQ = 3e10

# sun is at polar coordinates 0, 0

# average sun radius:  695 508 000 m

# average earth orbit: 149 600 000 000 m
# https://en.wikipedia.org/wiki/Earth%27s_orbit
# average earth radius: 6371.0 km -> 6 371 000 m
# orbital period 365.256363004 d -> 31 558 149 s
# https://en.wikipedia.org/wiki/Earth

# average moon orbit (around earth): 385 000 000 m
# https://en.wikipedia.org/wiki/Orbit_of_the_Moon
# average moon radius: 1737.4 km -> 1 737 400 m
# orbital period 27 d 7 h 43 min 11.5 s -> 2 361 592 s
# https://en.wikipedia.org/wiki/Moon

# average mars orbit: 228 000 000 000 m
# https://science.nasa.gov/mars/facts/
# average mars radius: 3389.5 km -> 3 389 500 m
# orbital period 686.980 d -> 59 355 072 s
# https://en.wikipedia.org/wiki/Mars

# randomize initial positions

# id: the id for the entity
# name: the english name of the entity
# or: orbital radius of the entity (m)
# orb_id: the id of the entity which this entity orbits
#         The sun will be set to -1 (no index), since it is not orbiting any modeled entities
# period: the orbiting period of the object (s)
# radius: radius of the entity (m)
# can_connect: if the entity can connect to the interplanetary internet
# orbital_direction: 1 for counter_clockwise, -1 for clockwise
initial_pos = [
    {  # Sun
        "id": 0,
        "name": "Sun",
        "orbital_radius": 0,
        "orb_id": -1,
        "period": 1,
        "radius": 695508000,
        "can_connect": False,
        "orbital_direction": 1,
    },
    {  # Earth
        "id": 1,
        "name": "Earth",
        "orbital_radius": 149600000000,
        "orb_id": 0,
        "period": 31558149,
        "radius": 6371000,
        "can_connect": True,
        "orbital_direction": 1,
    },
    {  # Mars
        "id": 2,
        "name": "Mars",
        "orbital_radius": 228000000000,
        "orb_id": 0,
        "period": 59355072,
        "radius": 3389500,
        "can_connect": True,
        "orbital_direction": 1,
    },
    {  # Moon
        "id": 3,
        "name": "The Moon",
        "orbital_radius": 385000000,
        "orb_id": 1,
        "period": 361592,
        "radius": 1737400,
        "can_connect": False,
        "orbital_direction": 1,
    },
    {  # ISS
        "id": 4,
        "name": "ISS",
        "orbital_radius": 6371000 + 400000,  # Earth radius + 400km
        "orb_id": 1,
        "period": 5580,
        "radius": 10,
        "can_connect": True,
        "orbital_direction": 1,
    },
    {  # Mars Orbiter
        "id": 5,
        "name": "Mars Orbiter",
        "orbital_radius": 3389500 + 400000,  # Mars radius + 400km
        "orb_id": 2,
        "period": 7200,
        "radius": 10,
        "can_connect": True,
        "orbital_direction": 1,
    },
]


# assume circular orbits
# x, y are the points for the orbital center
# radius is the radius of the orbit
# period is the period of the orbit
def calc_orbit_position(init_x, init_y, radius, period, time, orbital_direction):
    angle = time / period * 360.0 * orbital_direction

    y = math.sin(math.radians(angle)) * radius
    x = math.cos(math.radians(angle)) * radius

    return {"x": init_x + x, "y": init_y + y}


# search based on id
def search_entity_list(id, entities):
    default = -2
    return next((item for item in entities if item["id"] == id), default)


# recursive function to find the stats of id at time t
# t: time
# entity_stats: the target singular stats
# stat_lists: a list of all statistics on all entities
def get_entity_stats(t, entity_stats, stat_list):
    # search the initial list for the orbital id
    orb_id = entity_stats["orb_id"]
    assert orb_id >= 0
    orbital_stats = search_entity_list(orb_id, stat_list)

    # if the location of the orbital id entity has not been calculated, recurse to calculate
    if orbital_stats == -2:
        orbital_stats = get_entity_stats(
            t, search_entity_list(orb_id, initial_pos), stat_list
        )

    coords = calc_orbit_position(
        orbital_stats["x"],
        orbital_stats["y"],
        entity_stats["orbital_radius"],
        entity_stats["period"],
        t,
        entity_stats["orbital_direction"],
    )

    return {
        "id": entity_stats["id"],
        "name": entity_stats["name"],
        "orbital_radius": entity_stats["orbital_radius"],
        "orb_id": entity_stats["orb_id"],
        "period": entity_stats["period"],
        "radius": entity_stats["radius"],
        "can_connect": entity_stats["can_connect"],
        "orbital_direction": 1,
        "x": coords["x"],
        "y": coords["y"],
    }


# returns information for all entities at time time t
def get_stats(t: int):

    stats = []

    for entity in initial_pos:
        if entity["orb_id"] == -1:
            # is the sun
            stats.append(
                {
                    "id": 0,
                    "name": "Sun",
                    "orbital_radius": 0,
                    "orb_id": -1,
                    "period": 1,
                    "radius": 695508000,
                    "can_connect": False,
                    "orbital_direction": 1,
                    "x": 0,
                    "y": 0,
                }
            )
        else:
            entity_stats = get_entity_stats(t, entity, stats)
            stats.append(entity_stats)

    stats = get_connections(stats)

    return stats


# given two points to make a line, and a point
# find the closest distance from the point and
# the line.
# equation: https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points
# algorithm: https://stackoverflow.com/questions/849211/shortest-distance-between-a-point-and-a-line-segment
# (line_x1, line_y1), (line_x2, line_y2): 2 points making the line
# (point_x, point_y): point
def point_dist_to_line(
    line_x1: float,
    line_y1: float,
    line_x2: float,
    line_y2: float,
    point_x: float,
    point_y: float,
):
    a = point_x - line_x1
    b = point_y - line_y1
    c = line_x2 - line_x1
    d = line_y2 - line_y1

    lenSq = c * c + d * d
    param = -1

    if lenSq != 0:  # in case of 0 length line
        dot = a * c + b * d
        param = dot / lenSq

    xx = 0
    yy = 0

    if param < 0:
        xx = line_x1
        yy = line_y1
    elif param > 1:
        xx = line_x2
        yy = line_y2
    else:
        xx = line_x1 + param * c
        yy = line_y1 + param * d

    dx = point_x - xx
    dy = point_y - yy

    return math.sqrt(dx * dx + dy * dy)


# get the connections between any entities
# checking if an entity has a direct line of sight with the other entities
# takes in a data structure stats which has all of the meta data for all of the
# entities, including:
# "id": id of the entity
# "name": english name of the entity
# "orbital_radius": radius of the orbit (m)
# "orb_id": id of the entity which this entity orbits
# "period": orbital period (s)
# "radius": radius of the planet (m)
# "can_connect": entity able to connect to the interplanetary internet
# "x": x coordinate in space (m)
# "y": y coordinate in space (m)
def get_connections(stats):

    # If anyone has a better idea that isnt O(n^3) I am listening
    for entity_sending in stats:
        entity_sending["connections"] = []

        for entity_receiving in stats:
            # skips checking if 2 of the 3 identities are the same
            if (
                entity_receiving["id"] != entity_sending["id"]
                and entity_receiving["can_connect"]
                and entity_sending["can_connect"]
            ):
                blocking = False

                # check if entities are blocking
                for entity_blocking in stats:
                    if (
                        entity_receiving["id"]
                        != entity_blocking["id"]
                        != entity_sending["id"]
                    ):
                        dist = point_dist_to_line(
                            entity_sending["x"],
                            entity_sending["y"],
                            entity_receiving["x"],
                            entity_receiving["y"],
                            entity_blocking["x"],
                            entity_blocking["y"],
                        )

                        if dist < entity_blocking["radius"]:
                            blocking = True

                if not blocking:
                    dist = dist_between_points(
                        entity_receiving["x"],
                        entity_receiving["y"],
                        entity_sending["x"],
                        entity_sending["y"],
                    )
                    trans_time = transmission_time(dist)
                    err_rate = get_error_rate(entity_sending, entity_receiving)
                else:
                    dist = None
                    trans_time = None
                    err_rate = None

                entity_sending["connections"].append(
                    {
                        "id": entity_receiving["id"],
                        "name": entity_receiving["name"],
                        "connected": not blocking,
                        "distance": dist,
                        "trans_time": trans_time,
                        "error_rate": err_rate,
                    }
                )

    return stats


# sending messages at speed of light
# given a distance how long does it take
def transmission_time(dist):
    return dist / C


# pythagorean theorem
def dist_between_points(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# Calculate the free space path loss between 2 points
# https://en.wikipedia.org/wiki/Free-space_path_loss#Free-space_path_loss_formula
def free_space_path_loss(x1, y1, x2, y2) -> float:
    # Define the transmission frequency (30GHz, middle of Ka-band) and calculate wavelength
    wavelength = C / T_FREQ

    # Distance between the points in m
    distance = dist_between_points(x1, y1, x2, y2)

    # Assuming transmission/reception via isotropic antennas
    loss_ratio = (wavelength / (4 * math.pi * distance)) ** 2

    return loss_ratio


# Get the rate of transmission error between two satelites
def get_error_rate(sender, receiver) -> float:
    assert (
        "x" in sender.keys()
        and "y" in sender.keys()
        and "x" in receiver.keys()
        and "y" in receiver.keys()
    )
    return free_space_path_loss(sender["x"], sender["y"], receiver["x"], receiver["y"])


# for testing
# print(json.dumps(get_stats(0), indent=4))
