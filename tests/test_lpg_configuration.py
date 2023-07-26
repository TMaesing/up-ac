"""Test up AC implementation."""
from unified_planning.io import PDDLReader
import multiprocessing as mp
import time
import sys

sys.path.insert(0, '..')

from configurators import Configurator
from AC_interface import GenericACInterface

instances = ['../test_problems/depot/problem.pddl',
             '../test_problems/counters/problem.pddl']

instance_features = \
    {'../test_problems/depot/problem.pddl': [1,32,2,4],
     '../test_problems/counters/problem.pddl': [1,32,2,4]}

engine = ['lpg']

metrics = ['quality', 'runtime']

gaci = GenericACInterface()
gaci.read_engine_pcs(engine, '../engine_pcs')

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
