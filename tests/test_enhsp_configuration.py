"""Test up AC implementation."""
from unified_planning.io import PDDLReader
import multiprocessing as mp
import time
import sys
import os

path = os.getcwd().rsplit('up-ac', 2)[0]
path += 'up-ac'

if not os.path.isfile(sys.path[0] + '/configurators.py') and 'up-ac' in sys.path[0]:
    sys.path.insert(0, sys.path[0].rsplit('up-ac', 2)[0] + 'up-ac')

from configurators import Configurator
from AC_interface import GenericACInterface

instances = [f'{path}/test_problems/depot/problem.pddl',
             f'{path}/test_problems/counters/problem.pddl']

instance_features = \
    {f'{path}/test_problems/depot/problem.pddl': [1,32,2,4],
     f'{path}/test_problems/counters/problem.pddl': [1,32,2,4]}

engine = ['enhsp']
metrics = ['quality', 'runtime']

gaci = GenericACInterface()
gaci.read_engine_pcs(engine, f'{path}/engine_pcs')

if __name__ == '__main__':
    mp.freeze_support()

    for metric in metrics:

        AC = Configurator()

        AC.get_instance_features(instance_features)
        AC.set_training_instance_set(instances)
        AC.set_test_instance_set(instances)
        AC_fb_func = AC.get_feedback_function('SMAC', gaci, engine[0], metric, 'OneshotPlanner')
        AC.set_scenario('SMAC', gaci.engine_param_spaces[engine[0]],
                        configuration_time=120, n_trials=10,
                        min_budget=1, max_budget=2, crash_cost=0,
                        planner_timelimit=5, n_workers=3,
                        instance_features=AC.instance_features)

        incumbent, ac = AC.optimize('SMAC', feedback_function=AC_fb_func)
        AC.evaluate(AC_fb_func, AC.incumbent)
        AC.save_config('.', AC.incumbent, gaci, 'SMAC', engine[0])
