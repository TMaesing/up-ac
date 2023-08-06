"""Test up AC implementation."""
from unified_planning.io import PDDLReader
import multiprocessing as mp
import time
import sys
import os

# make sure test can be run from anywhere
path = os.getcwd().rsplit('up-ac', 2)[0]
path += 'up-ac'
if not os.path.isfile(sys.path[0] + '/configurators.py') and 'up-ac' in sys.path[0]:
    sys.path.insert(0, sys.path[0].rsplit('up-ac', 2)[0] + 'up-ac')

from configurators import Configurator
from AC_interface import GenericACInterface

# pddl instance to test with
instances = [f'{path}/test_problems/depot/problem.pddl',
             f'{path}/test_problems/counters/problem.pddl',
             f'{path}/test_problems/citycar/problem.pddl',
             f'{path}/test_problems/miconic/problem.pddl',
             f'{path}/test_problems/robot_fastener/problem.pddl']

print(instances)

# test setting
engine = ['tamer']

metrics = ['quality', 'runtime']

# initialize generic Algorithm Configuration interface
gaci = GenericACInterface()
gaci.read_engine_pcs(engine, f'{path}/engine_pcs')

# compute pddl instance features
instance_features = {}
for instance in instances:
    instance_features[instance] \
            = gaci.compute_instance_features(
                instance.rsplit('/', 1)[0] + '/domain.pddl',
                instance)

if __name__ == '__main__':
    mp.freeze_support()

    for metric in metrics:

        AC = Configurator()
        AC.set_training_instance_set(instances)
        AC.set_test_instance_set(instances)
        
        AC.set_scenario('OAT', engine[0], gaci.engine_param_spaces[engine[0]], gaci,
                            configuration_time=30, n_trials=30,
                            crash_cost=0,
                            planner_timelimit=15, n_workers=3,
                            instance_features=None, popSize=5, metric=metric, evlaLimit=1)
        AC_fb_func = AC.get_feedback_function('OAT', gaci, engine[0], metric, 'OneshotPlanner')
        # run algorithm configuration
        incumbent, _ = AC.optimize('OAT', feedback_function=AC_fb_func)
        # check configurations performance
        perf = AC.evaluate('OAT', metric, engine[0], 'OneshotPlanner', AC.incumbent, gaci)
        # save best configuration found
        AC.save_config('.', AC.incumbent, gaci, 'OAT', engine[0])
