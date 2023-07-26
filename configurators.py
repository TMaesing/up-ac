"""Functionalities for managing and calling configurators."""
from smac import Scenario
from smac import AlgorithmConfigurationFacade

from unified_planning.io import PDDLReader

from AC_interface import *

import json

class Configurator():
    """Configurator functions."""

    def __init__(self):
        """Initialize generic interface."""
        self.incumbent = None
        self.instance_features = {}
        self.train_set = {}
        self.test_set = {}
        self.reader = PDDLReader()
        self.metric = None
        self.crash_cost = 0
        self.ac = None

    def get_instance_features(self, instance_features=None):
        self.instance_features = instance_features
        print('\nSetting instance features.\n')

    def set_training_instance_set(self, train_set):
        self.train_set = train_set
        print('\nSetting training instance set.\n')

    def set_test_instance_set(self, test_set):
        self.test_set = test_set
        print('\nSetting testing instance set.\n')

    def get_feedback_function(self, ac_tool, gaci, engine, metric, mode):
        self.metric = metric
        if ac_tool == 'SMAC':
            def planner_feedback(config, instance, seed=0):
                instance_p = f'{instance}'
                domain_path = instance_p.rsplit('/', 1)[0]
                out_file = instance_p.rsplit('/', 1)[1]
                domain = f'{domain_path}/domain.pddl'
                pddl_problem = self.reader.parse_problem(f'{domain}',
                                                    f'{instance_p}')
                # print(pddl_problem)
                feedback = \
                    gaci.run_engine_config(ac_tool,
                                           config,
                                           metric,
                                           engine,
                                           mode,
                                           pddl_problem)
                if feedback is not None:
                    # SMAC always minimizes
                    if metric == 'quality':
                        return -feedback
                    elif metric == 'runtime':
                        return feedback
                else:
                    return None

            print('\nSMAC feedback function is generated.\n')

        return planner_feedback

    def set_scenario(self, ac_tool, param_space, configuration_time=120,
                     n_trials=400, min_budget=1, max_budget=3, crash_cost=0,
                     planner_timelimit=30, n_workers=1, instances=[],
                     instance_features=None):
        if not instances:
            instances = self.train_set
        self.crash_cost = crash_cost
        if ac_tool == 'SMAC':
            scenario = Scenario(
                param_space,
                walltime_limit=configuration_time,  # We want to optimize for <configuration_time> seconds
                n_trials=n_trials,  # We want to try max <n_trials> different trials
                min_budget=min_budget,  # Use min <min_budget> instance
                max_budget=max_budget,  # Use max <max_budget> instances
                deterministic=True, # Not stochastic algorithm
                crash_cost=crash_cost, # Cost of algorithm crashing -> AC metric to evaluate configuration
                trial_walltime_limit=planner_timelimit, # Max time for algorithm to run
                use_default_config=True, # include default config
                n_workers=n_workers, # Number of parallel runs
                instances=instances, # List of training instances
                instance_features=instance_features # Dict of instance features
            )
            print('\nSMAC scenario is set.\n')

        self.scenario = scenario

    def optimize(self, ac_tool, feedback_function=None, gray_box=False):
        if ac_tool == 'SMAC':
            print('\nStarting Parameter optimization\n')
            ac = AlgorithmConfigurationFacade(
                    self.scenario,
                    feedback_function,
                    overwrite=True,
                )

            self.incumbent = ac.optimize()

        print('\nBest Configuration found is:\n', self.incumbent)

        return self.incumbent, ac

    def evaluate(self, feedback_function, incumbent, instances=[]):
        if not instances:
            instances = self.test_set
        nr_inst = len(instances)
        avg_f = 0
        for inst in instances:
            f = feedback_function(incumbent, inst, seed=0)
            if f is not None and self.metric == 'quality':
                f = -f
            print(f'\nFeedback on instance {inst}:\n\n', f, '\n')
            if f is not None: 
                avg_f += f
            else:
                avg_f += self.crash_cost
                nr_inst -= 1
        avg_f = avg_f / nr_inst
        print('\nAverage performance:', avg_f, '\n')

    def save_config(self, path, config, gaci, ac_tool, engine):
        config = gaci.transform_conf_from_ac(ac_tool, engine, config)
        with open(f'{path}/incumbent_{engine}.json', 'w') as f:
            json.dump(config, f)
        print(f'\nSaved best configuration in {path}/incumbent_{engine}.json\n')
