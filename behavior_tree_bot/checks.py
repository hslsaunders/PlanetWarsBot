from behaviors import get_total_ally_ships,  get_total_enemy_ships, get_safe_future_adjusted_ship_sum
import logging, traceback, sys, os, inspect
logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)
def if_neutral_planet_available(state):
    return any(state.neutral_planets())

def has_sufficiently_largest_fleet(state):
    my_ships = get_safe_future_adjusted_ship_sum(state)
    enemy_ships = get_total_enemy_ships(state)
    return my_ships > enemy_ships * 1.1

def have_largest_fleet(state):
    return get_total_ally_ships(state) > get_total_enemy_ships(state)
