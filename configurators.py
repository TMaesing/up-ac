"""Functionalities for managing and calling configurators."""
from smac import Scenario
from smac import AlgorithmConfigurationFacade
from irace import irace

from unified_planning.io import PDDLReader

from AC_interface import *

import json
import timeit
import os
import urllib.request
import zipfile

class Configurator():
    """Configurator functions."""

    def __init__(self):
        """Initialize generic interface."""
        self.capabilities = {'quality': {'OneshotPlanner': ['lpg', 'fast-downward', 'enhsp', 'symk'], 'AnytimePlanner': ['fast-downward', 'symk']},
                             'runtime': {'OneshotPlanner': ['lpg', 'fast-downward', 'enhsp', 'symk', 'tamer', 'pyperplan'], 'AnytimePlanner': ['fast-downward', 'symk']}}
        self.incumbent = None
        self.instance_features = {}
        self.train_set = {}
        self.test_set = {}
        self.reader = PDDLReader()
        self.metric = None
        self.crash_cost = 0
        self.ac = None

        if not os.path.exists('OAT'):
            print('True')
            urllib.request.urlretrieve('https://docs.optano.com/algorithm.tuner/current/OPTANO.Algorithm.Tuner.Application.2.1.0_linux-x64.zip', 'OAT/OAT.zip')
            with zipfile.ZipFile('OAT/OAT.zip', 'r') as zip_ref:
                zip_ref.extractall('OAT')
            if os.path.isfile('OAT/OAT.zip'):
                os.remove('OAT/OAT.zip')




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
        if engine in self.capabilities[metric][mode]:
            self.metric = metric
            if ac_tool == 'SMAC':
                def planner_feedback(config, instance, seed=0):
                    if metric == 'runtime':
                        start = timeit.default_timer()
                    instance_p = f'{instance}'
                    domain_path = instance_p.rsplit('/', 1)[0]
                    out_file = instance_p.rsplit('/', 1)[1]
                    domain = f'{domain_path}/domain.pddl'
                    pddl_problem = self.reader.parse_problem(f'{domain}',
                                                        f'{instance_p}')
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
                        if metric == 'runtime':
                            feedback = timeit.default_timer() - start
                        else:
                            feedback = self.crash_cost
                        return feedback

            if ac_tool == 'irace':
                def planner_feedback(experiment, scenario):
                    start = timeit.default_timer()
                    instance_p = scenario['instances'][experiment['id.instance'] - 1]
                    domain_path = instance_p.rsplit('/', 1)[0]
                    out_file = instance_p.rsplit('/', 1)[1]
                    domain = f'{domain_path}/domain.pddl'
                    pddl_problem = self.reader.parse_problem(f'{domain}',
                                                        f'{instance_p}')
                    config = dict(experiment['configuration'])

                    feedback = \
                        gaci.run_engine_config(ac_tool,
                                               config,
                                               metric,
                                               engine,
                                               mode,
                                               pddl_problem)

                    runtime = timeit.default_timer() - start
                    if feedback is not None:
                        # SMAC always minimizes
                        if metric == 'quality':
                            feedback = {'cost': -feedback, 'time': runtime}
                            return feedback
                        elif metric == 'runtime':
                            feedback = {'cost': runtime, 'time': runtime}
                            return feedback
                    else:
                        if metric == 'runtime':
                            feedback = {'cost': runtime, 'time': runtime}
                        else:
                            feedback = feedback = {'cost': self.crash_cost, 'time': self.crash_cost}
                        return feedback

            return planner_feedback
        else:
            print(f'Algorithm Configuration for {metric} of {ac_tool} in {mode} is not supported.')
            return None

    def set_scenario(self, ac_tool, engine, param_space, gaci, configuration_time=120,
                     n_trials=400, min_budget=1, max_budget=3, crash_cost=0,
                     planner_timelimit=30, n_workers=1, instances=[],
                     instance_features=None, metric='runtime'):
        if not instances:
            instances = self.train_set
        self.crash_cost = crash_cost
        if ac_tool == 'SMAC':
            scenario = Scenario(
                param_space,
                walltime_limit=configuration_time,  # We want to optimize for <configuration_time> seconds
                n_trials=n_trials,  # Maximum number or algorithm runs
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

        if ac_tool == 'irace':
            default_conf = gaci.get_df_irace(param_space, engine)

            if metric == 'quality':
                test_type = 'friedman'
                capping = False
            elif metric == 'runtime':
                test_type = 't-test'
                capping = True
            # See https://mlopez-ibanez.github.io/irace/reference/defaultScenario.html
            scenario = dict(
                maxTime = configuration_time, # We want to optimize for <configuration_time> seconds
                instances = instances, # List of training instances
                debugLevel = 3, 
                digits = 10, # number of decimal places to be considered for the real parameters
                parallel=n_workers, # Number of parallel runs
                forbiddenFile = "forbidden.txt",
                logFile = "",
                initConfigurations=default_conf,
                nbConfigurations=8,
                deterministic = True,
                testType=test_type,
                capping=capping,
                boundMax=planner_timelimit)

            self.irace_param_space = gaci.irace_param_space

            print('\nIrace scenario is set.\n')

        self.scenario = scenario

    def optimize(self, ac_tool, feedback_function=None, gray_box=False):
        if feedback_function is not None:
            if ac_tool == 'SMAC':
                print('\nStarting Parameter optimization\n')
                ac = AlgorithmConfigurationFacade(
                    self.scenario,
                    feedback_function,
                    overwrite=True,
                    )

                self.incumbent = ac.optimize()

                self.incumbent = self.incumbent.get_dictionary()

            if ac_tool == 'irace':
                print('\nStarting Parameter optimization\n')
                ac = irace(self.scenario,
                    self.irace_param_space,
                    feedback_function
                    )
                self.incumbent = ac.run()

                self.incumbent = self.incumbent.to_dict(orient='records')[0]

            print('\nBest Configuration found is:\n', self.incumbent)

            return self.incumbent, ac
        else:
            return None, None

    def evaluate(self, ac_tool, metric, engine, mode, incumbent, gaci, instances=[]):
        if incumbent is not None:
            if not instances:
                instances = self.test_set
            nr_inst = len(instances)
            avg_f = 0
            for inst in instances:
                if metric == 'runtime':
                    start = timeit.default_timer()

                incumbent = gaci.transform_conf_from_ac(ac_tool, engine, incumbent)

                f = \
                    gaci.run_engine_config(ac_tool, incumbent,
                                           metric, engine,
                                           mode, inst)
                if metric == 'runtime' and f is None:
                    f = start = timeit.default_timer() - start
                if f is not None and self.metric == 'quality':
                    f = -f
                print(f'\nFeedback on instance {inst}:\n\n', f, '\n')
                if f is not None: 
                    avg_f += f
                else:
                    avg_f += self.crash_cost
            if nr_inst != 0:
                avg_f = avg_f / nr_inst
                print(f'\nAverage performance on {nr_inst} instances:', avg_f, '\n')
                return avg_f
            else:
                print('\nPerformance could not be evaluated. No plans found.')
                return None
        else:
            return None

    def save_config(self, path, config, gaci, ac_tool, engine):
        if config is not None:
            config = gaci.transform_conf_from_ac(ac_tool, engine, config)
            with open(f'{path}/incumbent_{engine}.json', 'w') as f:
                json.dump(config, f)
            print(f'\nSaved best configuration in {path}/incumbent_{engine}.json\n')
        else:
            print(f'No configuration was saved. It was {config}')
