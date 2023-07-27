"""Test pddl instance feature computation implementation."""
from unified_planning.io import PDDLReader
import sys
import os
from tarski.io import PDDLReader as treader

path = os.getcwd().rsplit('up-ac', 2)[0]
path += 'up-ac'

if not os.path.isfile(sys.path[0] + '/configurators.py') \
        and 'up-ac' in sys.path[0]:
    sys.path.insert(0, 
        sys.path[0].rsplit('up-ac', 2)[0] + 'up-ac')

from AC_interface import GenericACInterface
from configurators import Configurator

gaci = GenericACInterface()

test_problems = path + '/test_problems'
features = {}

for file in os.listdir(test_problems):
    if os.path.isfile(test_problems + '/' + file + '/problem.pddl'):
        features[test_problems + '/' + file + '/problem.pddl'] \
            = gaci.compute_instance_features(test_problems + '/' \
                + file + '/domain.pddl', test_problems + '/' \
                + file + '/problem.pddl')

print(features)
