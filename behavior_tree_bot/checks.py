def if_neutral_planet_available(state):
    return any(state.neutral_planets())

def has_sufficiently_largest_fleet(state):
    my_ships = get_total_ally_ships(state)
    enemy_ships = get_total_enemy_ships(state)
    return my_ships * .8 > enemy_ships

def have_largest_fleet(state):
    return get_total_ally_ships(state) > get_total_enemy_ships(state)

def get_total_ally_ships(state):
    return sum(planet.num_ships for planet in state.my_planets()) + sum(fleet.num_ships for fleet in state.my_fleets())

def get_total_enemy_ships(state):
    return sum(planet.num_ships for planet in state.enemy_planets()) + sum(fleet.num_ships for fleet in state.enemy_fleets())
