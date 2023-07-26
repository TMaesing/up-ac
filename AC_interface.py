"""Generic algorithm configuration interface for unified planning."""
import unified_planning
from unified_planning.environment import get_environment
from unified_planning.shortcuts import *
from utils.pcs_transform import transform_pcs
from utils.ac_feedback import qaul_feedback, runtime_feedback
import copy

from ConfigSpace.read_and_write import pcs


class GenericACInterface():
    """Generic AC interface."""

    def __init__(self):
        """Initialize generic interface."""
        self.environment = get_environment()
        self.available_engines = self.get_available_engines()
        self.engine_param_spaces = {}
        self.engine_param_types = {}

    def get_available_engines(self):
        """Get planning engines installed in up."""
        factory = unified_planning.engines.factory.Factory(self.environment)

        return factory.engines

    def read_engine_pcs(self, engines, pcs_dir):
        """Read in pcs file for engine.

        parameter engines: list of str, names of engines.
        parameter pcs_dir: str, path to directory with pcs files.
        """
        if pcs_dir[-1] != '/':
            pcs_dir = pcs_dir + '/'

        print('\n\npcs_dir',pcs_dir, '\n\n')

        for engine in engines:
            with open(pcs_dir + engine + '.pcs', 'r') as f:
                self.engine_param_spaces[engine] = pcs.read(f)

            with open(pcs_dir + engine + '.pcs', 'r') as f:
                lines = f.readlines()
                self.engine_param_types[engine] = {}
                for line in lines:
                    if '# FLAGS #' in line:
                        self.engine_param_types[engine]['-'+line.split(' ')[0]] = 'FLAGS'
                    elif '# FLAG' in line:
                        self.engine_param_types[engine]['-'+line.split(' ')[0]] = 'FLAG'

    def transform_conf_from_ac(self, ac_tool, engine, configuration):
        """Transform configuration to up engine format.

        parameter ac_tool: str, name of AC tool in use.
        parameter engines: list of str, names of engines.
        parameter configuration: list of str, names of engines.

        return config: dict, configuration.
        """
        if ac_tool == 'SMAC':
            config = transform_pcs(engine, configuration)
            if engine == 'lpg':
                del_list = []
                add_list = []
                for pname, pvalue in config.items():
                    if pname in self.engine_param_types:
                        if self.engine_param_types[pname] == 'FLAGS':
                            del_list.append(pname)
                            flag_pname = pname + '=' + config[pname]
                            add_list.append(flag_pname)
                        elif self.engine_param_types[pname] == 'FLAG':
                            if config[pname] == '1':
                                config[pname] = ''
                            else:
                                del_list.append(pname)

                for dl in del_list:
                    del config[dl]

                for al in add_list:
                    config[al] = ''

            if engine == 'fast-downward':

                evals = ['eager_greedy', 'eager_wastar',
                         'lazy_greedy', 'lazy_wastar']
                open_eval = ['epsilon_greedy', 'single']
                open_evals = ['pareto', 'tiebreaking',
                              'type_based']
                pruning = ['atom_centric_stubborn_sets']

                search_option = config['fast_downward_search_config'] + '('

                if 'evaluator' in config:
                    if config['evaluator'] in evals:
                        search_option += '[' + str(config['evaluator']) + '()], '
                    else:
                        search_option += str(config['evaluator']) + '(), '

                if 'open' in config:
                    if config['open'] not in open_eval and \
                        config['open'] not in open_evals:
                        search_option += '[' + str(config['open']) + '()], '
                    elif config['open'] in open_eval:
                        search_option += '[' + str(config['open']) + '(' + str(config['open_list_evals']) + ')], '
                    elif config['open'] in open_evals:
                        search_option += '[' + str(config['open']) + '([]' + str(config['open_list_evals']) + '])], '

                if config['evaluator'] == 'ehc':
                    search_option += 'preferred_usage=' + str(config['ehc_preferred_usage']) + ','

                if 'reopen_closed' in config:
                    search_option += 'reopen_closed=' + str(config['reopen_closed']) + ','

                if 'randomize_successors' in config:
                    search_option += 'randomize_successors=' + str(config['randomize_successors']) + ','

                if 'pruning' in config:
                    if config['pruning'] in pruning:
                        search_option += 'pruning=' + str(config['pruning']) + '(use_sibling_shortcut=' \
                            + config['atom_centric_stubborn_sets_use_sibling'] + \
                            ',atom_selection_strategy=' + config['atom_selection_strategy'] + '(), '
                    else:
                        search_option += 'pruning=' + str(config['pruning']) + '(),'

                search_option += 'cost_type=' + config['cost_type'] + ')'
                search_option = search_option.replace(" ", "")

                config = {'fast_downward_search_config': search_option}

        return config

    def transform_param_space(self, ac_tool, pcs):
        """Transform configuration to AC tool format.

        parameter pcs: ConfigSpace object, parameter space.
        parameter ac_tool: str, AC tool in use.

        return param_space: transformed parameter space.
        """
        if ac_tool == 'SMAC':  # SMAC uses ConfigSpace
            param_space = pcs

        return param_space

    def get_feedback(self, engine, fbtype, result):
        """Get feedback from planning engine after run.

        parameter engine: str, name of planning engine.
        parameter fbtype: str, type of feedback
        parameter result: object, planning result.
        """
        if fbtype == 'quality':
            feedback = qaul_feedback(engine, result)
        if fbtype == 'runtime':
            feedback = runtime_feedback(engine, result)
        if fbtype == 'gray_box':
            feedback = None

        return feedback

    def run_engine_config(self, ac_tool, config, metric, engine, plantype, problem):
        """Execute configurated engine run.

        paremer config: configuration of engine.
        parameter engine: str, engine name.
        parameter plantype: str, type of planning.

        return feedback: result from configurated engine run.
        """
        if plantype == 'OneshotPlanner':
            config = self.transform_conf_from_ac(ac_tool, engine, config)
            with OneshotPlanner(name=engine,
                                params=config) as planner:
                try:
                    result = planner.solve(problem)
                    if (result.status ==
                            up.engines.PlanGenerationResultStatus.
                            SOLVED_SATISFICING):
                        print("Result found.\n")
                    else:
                        print("No plan found.\n")
                    feedback = self.get_feedback(engine, metric, result)
                except:
                    print("No plan found.\n")
                    feedback = None

        return feedback
