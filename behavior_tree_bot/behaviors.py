import sys
from heapq import heappush, heappop
sys.path.insert(0, '../')
from planet_wars import issue_order
import logging, traceback, sys, os, inspect
logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)

# https://gist.github.com/Kodagrux/5b39358d812c0fd8eaf4
def remap(value, minInput, maxInput, minOutput, maxOutput):
	value = clamp(value, minInput, maxInput)

	inputSpan = maxInput - minInput
	outputSpan = maxOutput - minOutput

	scaledThrust = float(value - minInput) / float(inputSpan)

	return minOutput + (scaledThrust * outputSpan)

# https://gist.github.com/laundmo/b224b1f4c8ef6ca5fe47e132c8deab56
def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolate on the scale given by a to b, using t as the point on that scale.
    Examples
    --------
        50 == lerp(0, 100, 0.5)
        4.2 == lerp(1, 5, 0.8)
    """
    return (1 - t) * a + t * b

def get_future_planet_ships_and_owner(planet, state, time_later):
    planet_ships = planet.num_ships
    planet_owner = planet.owner
    my_fleets = state.my_fleets()
    enemy_fleets = state.enemy_fleets()
    fleets = my_fleets + enemy_fleets

    fleet_arrivals = []
    for index, fleet in enumerate(fleets):
        if fleet.destination_planet != planet.ID:
            continue
        heappush(fleet_arrivals, (fleet.turns_remaining, fleet.num_ships, fleet.owner)) # (time, amount, owner)

    current_time = 0

    while fleet_arrivals:
        time, fleet_ships, fleet_owner = heappop(fleet_arrivals)
        if planet_owner != 0:
            planet_ships += planet.growth_rate * (time - current_time)
        current_time = time
        while fleet_ships > 0:
            subtract_ships = planet_owner != fleet_owner
            used_ships = fleet_ships
            if subtract_ships:
                if planet_ships < used_ships:
                    used_ships = planet_ships
                planet_ships -= used_ships
                fleet_ships -= used_ships
            else:
                planet_ships += used_ships
                fleet_ships -= used_ships
            if planet_ships == 0 and fleet_ships > 0:
                planet_owner = fleet_owner
    if current_time < time_later and planet_owner != 0:
        planet_ships += planet.growth_rate * (time_later - current_time)

    return planet_ships, planet_owner
def get_future_planet_ships_and_owner_from_source(planet, state, source_planet):
    return get_future_planet_ships_and_owner(planet, state, state.distance(planet.ID, source_planet.ID))

def attack_weakest_enemy_planet(state):
    # (1) If we currently have a fleet in flight, abort plan.
    #if len(state.my_planets()) == 0:
    #    return False

    # (2) Find my strongest planet.
    strongest_planets = state.my_planets()
    strongest_planets.sort(key=lambda t: t.num_ships)
    strongest_planet = max(state.my_planets(), key=lambda t: t.num_ships, default=None)

    # (3) Find the weakest enemy planet.
    target_planet_score = {}
    target_planet_ships_required = {}
    if strongest_planet:
        for planet in state.enemy_planets():
            future_ships, future_owner = get_future_planet_ships_and_owner_from_source(planet, state, strongest_planet)
            required_ships = future_ships + 1
            if future_owner == 1:# or required_ships > strongest_planet.num_ships:
                continue
            score = remap(planet.growth_rate, 1, 5, 0, 3) + remap(required_ships, 1, 250, 4, 0)
            target_planet_score[planet] = score
            target_planet_ships_required[planet] = required_ships
            #if required_ships < lowest_required_future_ships:
            #    weakest_planet = planet
            #    lowest_required_future_ships = required_ships
    if len(target_planet_score) == 0:
        return False

    weakest_planet = max(target_planet_score, key=target_planet_score.get)
    #weakest_planet = min(state.enemy_planets(), key=lambda t: get_future_planet_ships_and_owner_from_source(t, state, strongest_planet), default=None)

    if not strongest_planet or not weakest_planet:
        # No legal source or destination
        return False
    else:
        # (4) Send half the ships from my strongest planet to the weakest enemy planet.
        #greatest_future_ships, owner = get_future_planet_ships_and_owner(weakest_planet, state, state.distance(strongest_planet.ID, weakest_planet.ID))
        return issue_order(state, strongest_planet.ID, weakest_planet.ID, target_planet_ships_required[weakest_planet])

def spread_to_weakest_neutral_planet(state):
    # (1) If we currently have a fleet in flight, just do nothing.
    #if len(state.my_fleets()) >= 1:
    #    return False

    # (2) Find my strongest planet.
    #strongest_planet = max(state.my_planets(), key=lambda p: p.num_ships, default=None)
    #logging.debug("strongest planet: {}".format(strongest_planet))

    # (3) Find the weakest neutral planet.
    #weakest_planet = min(state.neutral_planets(), key=lambda p: p.num_ships, default=None)
    #closest_planet = min(state.neutral_planets(), key=lambda p: state.distance(strongest_planet.ID, p.ID), default=None)

    #if strongest_planet is None:
    #    return False

    target_planet_score = {}
    attack_source_and_cost = {}
    for neutral_planet in state.neutral_planets():
        assigned_score = False
        for ally_planet in state.my_planets():
            dist = state.distance(ally_planet.ID, neutral_planet.ID)
            future_ships, future_owner = get_future_planet_ships_and_owner(neutral_planet, state, dist)
            growth_rate = neutral_planet.growth_rate
            score = remap(dist, 0, 30, 1, 0) + remap(future_ships, 0, 200, 4, 0) + remap(growth_rate, 1, 5, 0, 2.5)
            #logging.debug("{}: dist: {}, num ships: {}, growth rate: {}, score: {}".format(neutral_planet.ID, dist, future_ships, growth_rate, score))
            #logging.debug("{}: actual ships {}, vs projected ships: {}, old owner: {}, new owner: {}".format(neutral_planet.ID, neutral_planet.num_ships, future_ships, neutral_planet.owner, future_owner))
            num_ships_required = future_ships + 1
            if future_owner == 1 or num_ships_required >= ally_planet.num_ships:
                continue
            if not assigned_score:
                target_planet_score[neutral_planet] = score
            elif score < target_planet_score[neutral_planet]:
                target_planet_score[neutral_planet] = score
            else:
                continue
            attack_source_and_cost[neutral_planet] = ally_planet, num_ships_required
            assigned_score = True

    target_planet = max(target_planet_score, key=target_planet_score.get, default=None)
    if target_planet is None:
        # No legal source or destination
        return False

    source_planet, num_ships = attack_source_and_cost[target_planet]

    #if strongest_planet.num_ships > 15:
    # (4) Send half the ships from my strongest planet to the weakest enemy planet.
    #num_ships = attack_source_and_cost[target_planet]#min(strongest_planet.num_ships / 2, target_planet.num_ships + 3)
    #logging.debug("sending {} to {}".format(num_ships, target_planet.ID))
    return issue_order(state, source_planet.ID, target_planet.ID, num_ships)

def try_steal_cheap_planet(state):
    cheapest_planet = None
    source_planet = None
    num_ships = 9999
    shortest_dist_to_planet = {}
    for enemy_planet in state.enemy_planets():
        for ally_planet in state.my_planets():
            dist = state.distance(enemy_planet.ID, ally_planet.ID)
            if enemy_planet not in shortest_dist_to_planet or dist < shortest_dist_to_planet[enemy_planet]:
                shortest_dist_to_planet[enemy_planet] = dist

            future_planet_ships, owner = get_future_planet_ships_and_owner_from_source(enemy_planet, state, ally_planet)
            required_ships = future_planet_ships + 1
            if owner == 1:
                continue
            if required_ships <= ally_planet.num_ships * 0.25 and required_ships < num_ships:
                cheapest_planet = enemy_planet
                source_planet = ally_planet
                num_ships = required_ships
    if cheapest_planet is None:
        return False

    return issue_order(state, source_planet.ID, cheapest_planet.ID, num_ships)

def try_save_doomed_ally(state):
    target, cheapest_rescuer, fewest_ships = None, None, 9999
    for ally_planet in state.my_planets():
        for planet_to_the_rescue in state.my_planets():
            if planet_to_the_rescue == ally_planet:
                continue
            future_planet_ships, future_owner = get_future_planet_ships_and_owner_from_source(ally_planet, state, planet_to_the_rescue)
            rescue_planet_future_ships, rescue_planet_future_owner = get_future_planet_ships_and_owner(planet_to_the_rescue, state, 0)
            if future_owner != 1:
                required_ships = future_planet_ships + 1
                if rescue_planet_future_ships > required_ships and required_ships < fewest_ships:
                    target = ally_planet
                    cheapest_rescuer = planet_to_the_rescue
                    fewest_ships = required_ships
    if not cheapest_rescuer:
        return False
    return issue_order(state, cheapest_rescuer.ID, target.ID, fewest_ships)


def spread_to_weakest_ally(state):
    score = {}
    #for planet in state.my_planets():
    #    score =


