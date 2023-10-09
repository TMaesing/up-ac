"""Functionalities for managing and calling configurators."""
from smac import Scenario
from smac import AlgorithmConfigurationFacade
from unified_planning.exceptions import UPProblemDefinitionError, UPException
from pebble import concurrent
import os
import dill
import sys
from concurrent.futures import TimeoutError

from up_ac.AC_interface import *
from up_ac.configurators import Configurator

import timeit


class SmacConfigurator(Configurator):
    """Configurator functions."""

    def __init__(self):
        """Initialize Smac configurator."""
        Configurator.__init__(self)
        self.crash_cost = 0
        self.planner_timelimit = 0
        self.engine = None
        self.gaci = None 

    def get_feedback_function(self, gaci, engine, metric, mode,
                              gray_box=False):
        """
        Generate the function to run engine and get feedback.

        parameter gaci: AC interface object.
        parameter engine: str, engine name.
        parameter metric: str, 'runtime' or 'quality'
        parameter mode: str, type of planning.
        parameter gray_box: True, if gra box to use

        return planner_feedback: function, planner feedback function.
        """
        if engine in self.capabilities[metric][mode]:
            self.metric = metric

            def planner_feedback(config, instance, seed, reader):
                start = timeit.default_timer()
                instance_p = f'{instance}'
                domain_path = instance_p.rsplit('/', 1)[0]
                domain = f'{domain_path}/domain.pddl'
                pddl_problem = reader.parse_problem(f'{domain}',
                                                    f'{instance_p}')

                # Since Smac handles time limits itself,
                # we do not use concurrent, as with other AC tools
                try:
                    feedback = \
                        gaci.run_engine_config(config,
                                               metric,
                                               engine,
                                               mode,
                                               pddl_problem)
                except (AssertionError, NotImplementedError,
                        UPProblemDefinitionError, UPException,
                        UnicodeDecodeError) as err:
                    print('\n** Error in planning engine!', err)
                    if metric == 'runtime':
                        feedback = self.planner_timelimit
                    elif metric == 'quality':
                        feedback = self.crash_cost
                '''

                try:
                    @concurrent.process(timeout=self.planner_timelimit)
                    def solve(config, metric, engine,
                              mode, pddl_problem):
                        print('Running further\n')
                        feedback = \
                            gaci.run_engine_config(config,
                                                   metric, engine,
                                                   mode, pddl_problem)

                        return feedback

                    feedback = solve(config, metric, engine,
                                     mode, pddl_problem)
                    
                    try:
                        feedback = feedback.result()
                    except TimeoutError:
                        if metric == 'runtime':
                            feedback = self.planner_timelimit
                        elif metric == 'quality':
                            feedback = self.crash_cost

                except (AssertionError, NotImplementedError,
                        UPProblemDefinitionError):
                    print('\n** Error in planning engine!')
                    if metric == 'runtime':
                        feedback = self.planner_timelimit
                    elif metric == 'quality':
                        feedback = self.crash_cost
                '''
              
                if feedback is not None:
                    # SMAC always minimizes
                    if metric == 'quality':
                        self.print_feedback(engine, instance, feedback)
                        return -feedback
                    # Solving runtime optimization by passing
                    # runtime as result, since smac minimizes it
                    elif metric == 'runtime':
                        if engine in ('tamer', 'pyperplan'):
                            feedback = timeit.default_timer() - start
                            self.print_feedback(engine, instance, feedback)
                        else:
                            feedback = feedback
                            self.print_feedback(engine, instance, feedback)
                        return feedback
                else:
                    # Penalizing failed runs
                    if metric == 'runtime':
                        # Penalty is max runtime in runtime scenario
                        feedback = self.scenario.trial_walltime_limit
                        self.print_feedback(engine, instance, feedback)
                    else:
                        # Penalty is defined by user in quality scenario
                        feedback = self.crash_cost
                        self.print_feedback(engine, instance, feedback)

                    return feedback

            path = os.getcwd().rsplit('up-ac', 1)[0]
            path += 'up-ac/up_ac/utils'

            self.feedback_path = path

            dill.dump(
                planner_feedback, open(
                    f'{path}/feedback.pkl', 'wb'),
                recurse=True)

            return planner_feedback
        else:
            print(f'Algorithm Configuration for {metric} of {engine}' + \
                  f' in {mode} is not supported.')
            return None

    def set_scenario(self, engine, param_space, gaci,
                     configuration_time=120, n_trials=400, min_budget=1,
                     max_budget=3, crash_cost=0, planner_timelimit=30,
                     n_workers=1, instances=[], instance_features=None,
                     metric='runtime'):
        """
        Set up algorithm configuration scenario.

        parameter engine: str, which engine.
        parameter param_space: ConfigSpace object.
        parameter gaci: AC interface object.
        parameter configuration_time: int, overall configuration time budget.
        parameter n_trials: int, max number of engine evaluations.
        parameter min_budget: int, min number of instances to use.
        parameter max_budget: int, max number of instances to use.
        parameter crash_cost: int, which cost to use if engine fails.
        parameter planner_timelimit: int, max runtime per evaluation.
        parameter n_workers: int, no. of cores to utilize.
        parameter instances: list, problem instance paths.
        parameter instance_features: dict, inst names and lists of features.
        parameter metric: str, optimization metric.
        """
        if not instances:
            instances = self.train_set
        self.crash_cost = crash_cost
        self.planner_timelimit = planner_timelimit
        self.engine = engine
        self.gaci = gaci
        scenario = Scenario(
            param_space,
            # We want to optimize for <configuration_time> seconds
            walltime_limit=configuration_time,
            n_trials=n_trials,  # Maximum number or algorithm runs
            min_budget=min_budget,  # Use min <min_budget> instance
            max_budget=max_budget,  # Use max <max_budget> instances
            deterministic=True,  # Not stochastic algorithm
            # Cost of algorithm crashing -> AC metric to evaluate configuration
            crash_cost=crash_cost,  
            # Max time for algorithm to run
            trial_walltime_limit=planner_timelimit,  
            use_default_config=True,  # include default config
            n_workers=n_workers,  # Number of parallel runs
            instances=instances,  # List of training instances
            instance_features=instance_features  # Dict of instance features
        )
        print('\nSMAC scenario is set.\n')

        self.scenario = scenario

    def optimize(self, feedback_function=None, gray_box=False):
        """
        Run the algorithm configuration.

        parameter feedback_function: function to run engine and get feedback.
        parameter gray_box: True, if gray box usage.
        """
        if feedback_function is not None:
            # Import feedback function, since dask cannot pickle local objects            
            path = os.getcwd().rsplit('up-ac', 1)[0]
            path += 'up-ac/up_ac/utils'
            sys.path.append(r"{}".format(path))
            from load_smac_feedback import get_feedback

            print('\nStarting Parameter optimization\n')
 
            ac = AlgorithmConfigurationFacade(
                self.scenario,
                get_feedback,
                overwrite=True)

            self.incumbent = ac.optimize()

            self.incumbent = self.incumbent.get_dictionary()

            print('\nBest Configuration found is:\n',
                  self.incumbent)

            return self.incumbent, None
        else:
            return None, None
