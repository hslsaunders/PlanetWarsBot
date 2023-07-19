import sys
from heapq import heappush, heappop
sys.path.insert(0, '../')
from planet_wars import issue_order
from math import ceil
import logging, traceback, sys, os, inspect
logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

def get_total_ally_ships_in_planets(state):
    return sum(planet.num_ships for planet in state.my_planets())

def get_total_enemy_ships_in_planets(state):
    return sum(planet.num_ships for planet in state.my_planets())
def get_total_ally_ships(state):
    return get_total_ally_ships_in_planets(state) + sum(fleet.num_ships for fleet in state.my_fleets())

def get_total_enemy_ships(state):
    return sum(planet.num_ships for planet in state.enemy_planets()) + sum(fleet.num_ships for fleet in state.enemy_fleets())

def get_safe_future_adjusted_planet_ship_sum(state, planet):
    future_ships, future_owner = get_future_planet_ships_and_owner(planet, state, 0)
    if future_owner == 1:
        if future_ships < planet.num_ships:
            return future_ships
        else:
            return planet.num_ships
    else:
        return -future_ships

def get_safe_future_adjusted_ship_sum(state):
    adjusted_sum = 0
    for planet in state.my_planets():
        adjusted_sum += get_safe_future_adjusted_planet_ship_sum(state, planet)
    return adjusted_sum

def clamp(num, min_value, max_value):
    return max(min(num, max_value), min_value)

# https://gist.github.com/Kodagrux/5b39358d812c0fd8eaf4
def remap_unconstrained(value, minInput, maxInput, minOutput, maxOutput):
    inputSpan = maxInput - minInput
    outputSpan = maxOutput - minOutput

    scaledThrust = float(value - minInput) / float(inputSpan)

    return minOutput + (scaledThrust * outputSpan)
def remap(value, minInput, maxInput, minOutput, maxOutput):
    return remap_unconstrained(clamp(value, minInput, maxInput), minInput, maxInput, minOutput, maxOutput)

# https://gist.github.com/laundmo/b224b1f4c8ef6ca5fe47e132c8deab56
def lerp(a: float, b: float, t: float) -> float:
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

def attack_strong_and_vulnerable_enemy_planet(state):
    ship_sum = get_safe_future_adjusted_ship_sum(state)

    target_planet_score = {}
    target_planet_ships_required = {}
    for planet in state.enemy_planets():
        future_ships, future_owner = get_future_planet_ships_and_owner(planet, state, 0)
        required_ships = future_ships + 1
        if future_owner == 1 or required_ships > ship_sum:
            continue
        score = remap(planet.growth_rate, 1, 5, 0, 3) + remap(required_ships, 1, 250, 4, 0)
        target_planet_score[planet] = score
        target_planet_ships_required[planet] = required_ships

    if len(target_planet_score) == 0:
        return False

    target_planet = max(target_planet_score, key=target_planet_score.get)
    ships_required = target_planet_ships_required[target_planet]

    sorted_ally_planets = state.my_planets()
    sorted_ally_planets.sort(key=lambda t: t.num_ships, reverse=True)

    ships_accumulated = 0
    planet_contributions = {}
    allowed_contributions = {}
    allowed_contributions_sum = 0
    index = 0
    while ships_accumulated < ships_required:
        planet = sorted_ally_planets[index]
        if planet not in allowed_contributions:
            future_ships, future_owner = get_future_planet_ships_and_owner(planet, state, 0)
            if future_owner != 1:
                allowed_contribution = 0
            else:
                allowed_contribution = get_safe_future_adjusted_planet_ship_sum(state, planet)
            allowed_contributions[planet] = allowed_contribution
        else:
            allowed_contribution = allowed_contributions[planet]
        allowed_contributions_sum += allowed_contribution
        current_contributions = planet_contributions[planet] if planet in planet_contributions else 0
        contribution = min(ceil((allowed_contribution - current_contributions) / 2), ships_required - ships_accumulated)
        ships_accumulated += contribution
        planet_contributions[planet] = current_contributions + contribution
        index = (index + 1) % len(sorted_ally_planets)
        if index == 0 and allowed_contributions_sum < ships_required:
            return False

    for planet in planet_contributions:
        if not issue_order(state, planet.ID, target_planet.ID, planet_contributions[planet]):
            return False
    return True

def spread_to_weakest_neutral_planet(state):
    target_planet_score = {}
    attack_source_and_cost = {}
    for neutral_planet in state.neutral_planets():
        assigned_score = False
        for ally_planet in state.my_planets():
            dist = state.distance(ally_planet.ID, neutral_planet.ID)
            closest_dist_to_enemy = float('inf')
            for enemy_planet in state.enemy_planets():
                neutral_to_enemy_dist = state.distance(enemy_planet.ID, neutral_planet.ID)
                if neutral_to_enemy_dist < closest_dist_to_enemy:
                    closest_dist_to_enemy = neutral_to_enemy_dist

            future_ships, future_owner = get_future_planet_ships_and_owner(neutral_planet, state, dist)
            growth_rate = neutral_planet.growth_rate
            score = remap_unconstrained(dist, 0, 15, 1, -2) + remap(future_ships, 0, 200, 4, 0) + remap(growth_rate, 1, 5, 0, 2.5) + remap(closest_dist_to_enemy, 0, 15, -2, 0)
            num_ships_required = future_ships + 1

            if future_owner == 1 or num_ships_required >= get_safe_future_adjusted_planet_ship_sum(state, ally_planet):
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
        return False

    source_planet, num_ships = attack_source_and_cost[target_planet]

    return issue_order(state, source_planet.ID, target_planet.ID, num_ships)

def try_steal_cheap_planet(state):
    planet_costs = {}
    for enemy_planet in state.enemy_planets():
        shortest_dist_to_planet = float('inf')
        for ally_planet in state.my_planets():
            dist = state.distance(enemy_planet.ID, ally_planet.ID)
            if dist < shortest_dist_to_planet:
                shortest_dist_to_planet = dist

            future_planet_ships, my_future_owner = get_future_planet_ships_and_owner_from_source(enemy_planet, state, ally_planet)
            required_ships = future_planet_ships + 1
            ally_planet_num_ships_cutoff = ally_planet.num_ships * 0.25
            if my_future_owner == 1:
                continue

            my_future_ships, my_future_owner = get_future_planet_ships_and_owner(ally_planet, state, 0)
            if my_future_owner != 1:
                continue
            if required_ships <= ally_planet_num_ships_cutoff and (enemy_planet not in planet_costs or required_ships < planet_costs[enemy_planet][0]):
                planet_costs[enemy_planet] = required_ships, ally_planet

        if shortest_dist_to_planet > 15 and enemy_planet in planet_costs:
            del planet_costs[enemy_planet]

    if len(planet_costs) == 0:
        return False

    cheapest_planet = min(planet_costs, key=planet_costs.get)

    if cheapest_planet is None:
        return False

    num_ships, source_planet = planet_costs[cheapest_planet]
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


