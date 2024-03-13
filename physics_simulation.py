import math

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
# or: orbital radius of the entity (m)
# orb_id: the id of the entity which this entity orbits
#         The sun will be set to -1 (no index), since it is not orbiting any modeled entities
# period: the orbiting period of the object (s)
# radius: radius of the entity (m)
initial_pos = [
    { # Sun
        "id": 0,
        "or": 0,
        "orb_id": -1,
        "period": 1,
        "radius": 695508000
    },{ # Earth
        "id": 1,
        "or": 149600000000,
        "orb_id": 0,
        "period": 31558149,
        "radius": 6371000
    },{ # Mars
        "id": 2,
        "or": 228000000000,
        "orb_id": 0,
        "period": 59355072,
        "radius": 3389500
    },{ # Moon
        "id": 3,
        "or": 385000000,
        "orb_id": 1,
        "period": 361592,
        "radius": 1737400
    },{ # ISS
        "id": 4,
        "or": 6371000 + 400000, # Earth radius + 400km
        "orb_id": 1,
        "period": 5580,
        "radius": 10
    },{ # Mars Orbiter
        "id": 5,
        "or": 3389500 + 400000, # Mars radius + 400km
        "orb_id": 2,
        "period": 7200,
        "radius": 10
    }
]



# assume circular orbits
# x, y are the points for the orbital center
# radius is the radius of the orbit
# period is the period of the orbit
def calc_orbit_position(init_x, init_y, radius, period, time):
    angle = time/period * 360.0

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
    assert(orb_id >= 0)
    orbital_stats = search_entity_list(orb_id, stat_list)

    # if the location of the orbital id entity has not been calculated, recurse to calculate
    if orbital_stats == -2:
        orbital_stats = get_entity_stats(t, search_entity_list(orb_id, initial_pos), stat_list)

    coords = calc_orbit_position(orbital_stats["x"], orbital_stats["y"], entity_stats["or"], entity_stats["period"], t)

    return {
        "id": entity_stats["id"],
        "or": entity_stats["or"],
        "orb_id": entity_stats["orb_id"],
        "period": entity_stats["period"],
        "radius": entity_stats["radius"],
        "x": coords["x"],
        "y": coords["y"]
    }


# returns information for all entities at time time t
def get_stats(t):

    stats = []

    for entity in initial_pos:
        if entity["orb_id"] == -1:
            # is the sun
            stats.append(
                {
                    "id": 0,
                    "or": 0,
                    "orb_id": -1,
                    "period": 1,
                    "radius": 695508000,
                    "x": 0,
                    "y": 0
                }
            )
        else:
            entity_stats = get_entity_stats(t, entity, stats)
            stats.append(entity_stats)

    return stats
