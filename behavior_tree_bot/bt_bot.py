#!/usr/bin/env python
#

"""
// There is already a basic strategy in place here. You can use it as a
// starting point, or you can throw it out entirely and replace it with your
// own.
"""
import logging, traceback, sys, os, inspect
logging.basicConfig(filename=__file__[:-3] +'.log', filemode='w', level=logging.DEBUG)
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from behavior_tree_bot.behaviors import *
from behavior_tree_bot.checks import *
from behavior_tree_bot.bt_nodes import Selector, Sequence, Action, Check, LoopUntilFailed, AlwaysSucceed

from planet_wars import PlanetWars, finish_turn


# You have to improve this tree or create an entire new one that is capable
# of winning against all the 5 opponent bots
def setup_behavior_tree():

    # Top-down construction of behavior tree
    root = Sequence(name='High Level Ordering of Strategies')

    offensive_plan = Sequence(name='Offensive Strategy')
    offense_succeeder = AlwaysSucceed(offensive_plan)

    full_attack_plan = Sequence(name='Full Offense')
    ready_for_full_attack = Check(has_sufficiently_largest_fleet)
    full_attack = Action(attack_weakest_enemy_planet)
    full_attack_loop = LoopUntilFailed(child_node=full_attack)
    full_attack_plan.child_nodes = [ready_for_full_attack, full_attack_loop]#[largest_fleet_check, attack]
    full_attack_succeeder = AlwaysSucceed(full_attack_plan)

    cheap_steals_attack = Action(try_steal_cheap_planet)
    cheap_steal_loop = LoopUntilFailed(child_node=cheap_steals_attack, name="Attack Loop")

    offensive_plan.child_nodes = [full_attack_succeeder, cheap_steal_loop]

    defensive_plan = Sequence(name="Defensive Strategy")
    save_doomed_ally = Action(try_save_doomed_ally)
    save_doomed_ally_loop = LoopUntilFailed(child_node=save_doomed_ally, name="Savior Loop")
    defensive_plan.child_nodes = [save_doomed_ally_loop]
    defense_succeeder = AlwaysSucceed(defensive_plan)

    spread_sequence = Sequence(name='Spread Strategy')
    #neutral_planet_check = Check(if_neutral_planet_available)
    neutral_planet_spread = Action(spread_to_weakest_neutral_planet)
    neutral_spread_loop = LoopUntilFailed(child_node=neutral_planet_spread, name="Spread Loop")

    #should_distribute_to_allies = Check()
    #ally_distribution_spread = Action(spread_to_weakest_ally)

    spread_sequence.child_nodes = [neutral_spread_loop]

    root.child_nodes = [offense_succeeder, defense_succeeder, spread_sequence]

    logging.info('\n' + root.tree_to_string())
    return root

# You don't need to change this function
def do_turn(state):
    behavior_tree.execute(planet_wars)

if __name__ == '__main__':
    logging.basicConfig(filename=__file__[:-3] + '.log', filemode='w', level=logging.DEBUG)

    behavior_tree = setup_behavior_tree()
    try:
        map_data = ''
        while True:
            current_line = input()
            if len(current_line) >= 2 and current_line.startswith("go"):
                planet_wars = PlanetWars(map_data)
                do_turn(planet_wars)
                finish_turn()
                map_data = ''
            else:
                map_data += current_line + '\n'

    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
    except Exception:
        traceback.print_exc(file=sys.stdout)
        logging.exception("Error in bot.")
