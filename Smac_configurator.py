"""Functionalities for managing and calling configurators."""
from smac import Scenario
from smac import AlgorithmConfigurationFacade

from AC_interface import *
from configurators import Configurator

import timeit

class SmacConfigurator(Configurator):
    """Configurator functions."""

    def __init__(self):
        """Initialize Smac configurator."""
        Configurator.__init__(self)

    def get_feedback_function(self, ac_tool, gaci, engine, metric, mode, gray_box=False):
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

                return planner_feedback
        else:
            print(f'Algorithm Configuration for {metric} of {ac_tool} in {mode} is not supported.')
            return None

    def set_scenario(self, ac_tool, engine, param_space, gaci, configuration_time=120,
                     n_trials=400, min_budget=1, max_budget=3, crash_cost=0,
                     planner_timelimit=30, n_workers=1, instances=[],
                     instance_features=None, metric='runtime', popSize=128, evlaLimit=2147483647):
        if not instances:
            instances = self.train_set
        self.crash_cost = crash_cost
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

        self.scenario = scenario

    def optimize(self, ac_tool, feedback_function=None, gray_box=False):
        if feedback_function is not None:
            print('\nStarting Parameter optimization\n')
            ac = AlgorithmConfigurationFacade(
                self.scenario,
                feedback_function,
                overwrite=True,
                )

            self.incumbent = ac.optimize()

            self.incumbent = self.incumbent.get_dictionary()

            print(f'\nBest Configuration found by {ac_tool} is:\n', self.incumbent)

            return self.incumbent, None
        else:
            return None, None
