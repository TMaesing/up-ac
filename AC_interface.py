"""Generic algorithm configuration interface for unified planning."""
import unified_planning
from unified_planning.environment import get_environment
from unified_planning.shortcuts import *
from utils.pcs_transform import transform_pcs
from utils.ac_feedback import qaul_feedback, runtime_feedback
from utils.patches import patch_pcs
import copy
from tarski.io import PDDLReader as treader
import pandas as pd
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

from ConfigSpace.read_and_write import pcs
from ConfigSpace.hyperparameters import (
    CategoricalHyperparameter,
    UniformFloatHyperparameter,
    UniformIntegerHyperparameter,
)
from ConfigSpace.conditions import (
AndConjunction,
EqualsCondition
)

pcs = patch_pcs(pcs)


class GenericACInterface():
    """Generic AC interface."""

    def __init__(self):
        """Initialize generic interface."""
        self.environment = get_environment()
        self.available_engines = self.get_available_engines()
        self.engine_param_spaces = {}
        self.engine_param_types = {}
        self.treader = treader(raise_on_error=True)

    def get_available_engines(self):
        """Get planning engines installed in up."""
        factory = unified_planning.engines.factory.Factory(self.environment)

        return factory.engines

    def compute_instance_features(self, domain, instance):
        """Compute some instance features of a iven pddl instance.

        parameter domain: pddl, problem domain.
        parameter instance: pddl, problem instance.

        return features: list, computed instance features
        """
        try:
            # TODO catch duplicte errors in tarski
            features = []
            self.treader.parse_domain(domain)
            problem = self.treader.parse_instance(instance)
            lang = problem.language
            features.append(len(lang.predicates))
            features.append(len(lang.functions))
            features.append(len(lang.constants()))
            features.append(len(list(problem.actions)))
            features.append(features[1] / features[0])
            features.append(features[1] / features[2])
            features.append(features[1] / features[3])
            features.append(features[0] / features[2])
            features.append(features[0] / features[3])
            features.append(features[2] / features[3])
        except:
            features = [0 for _ in range(10)]

        return features

    def read_engine_pcs(self, engines, pcs_dir):
        """Read in pcs file for engine.

        parameter engines: list of str, names of engines.
        parameter pcs_dir: str, path to directory with pcs files.
        """
        if pcs_dir[-1] != '/':
            pcs_dir = pcs_dir + '/'

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
        parameter configuration: dict, parameter names with values.

        return config: dict, configuration.
        """
        if ac_tool == 'SMAC' or ac_tool == 'irace':
            config = transform_pcs(engine, configuration)
            if engine == 'lpg':
                del_list = []
                add_list = []
                for pname, pvalue in config.items():
                    if pname in self.engine_param_types['lpg']:
                        if self.engine_param_types['lpg'][pname] == 'FLAGS':
                            del_list.append(pname)
                            flag_pname = pname + '=' + config[pname]
                            add_list.append(flag_pname)
                        elif self.engine_param_types['lpg'][pname] == 'FLAG':
                            if config[pname] == '1':
                                config[pname] = ''
                            else:
                                del_list.append(pname)

                for dl in del_list:
                    del config[dl]

                for al in add_list:
                    config[al] = ''

            if engine == 'fast-downward' or engine == 'symk':

                evals = ['eager_greedy', 'eager_wastar',
                         'lazy_greedy', 'lazy_wastar']
                open_eval = ['epsilon_greedy', 'single']
                open_evals = ['pareto', 'tiebreaking',
                              'type_based']
                pruning = ['atom_centric_stubborn_sets']

                if len(config) == 1:
                    pass
                else:
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

                    if 'evaluator' in config:
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

                    if engine == 'fast-downward':
                        config = {'fast_downward_search_config': search_option}
                    else:
                        config = {'symk_search_config': search_option}

            else:
                config = configuration

        elif ac_tool == 'OAT':
            config = configuration

        return config

    def get_ps_irace(self, param_space):

        conditionals = param_space.get_all_conditional_hyperparameters()
        params = param_space.get_hyperparameters_dict()

        names = []
        values = []
            
        for _, param in params.items():
            names.append(param.name)
            values.append(param.default_value)

        default_conf = pd.DataFrame([values], columns=names)

        with (ro.default_converter + pandas2ri.converter).context():
            default_conf = ro.conversion.get_conversion().py2rpy(default_conf)

        irace_param_space = ''

        for p, param in params.items():
            condition = ''
            if isinstance(param, CategoricalHyperparameter):
                choices = ''
                for pc in param.choices:
                    choices += f'\"{pc}\", '
                irace_param_space += '\n' + param.name + ' \"\" c ' + f'({choices[:-2]})' + condition
            elif isinstance(param, UniformFloatHyperparameter):
                irace_param_space += '\n' + param.name + ' \"\" r ' + f'({param.lower}, {param.upper})' + condition
            elif isinstance(param, UniformIntegerHyperparameter):
                irace_param_space += '\n' + param.name + ' \"\" i ' + f'({param.lower}, {param.upper})' + condition

        forbidden = ''
        for f in param_space.forbidden_clauses:
            fpair = f.get_descendant_literal_clauses()
            if isinstance(fpair[0].hyperparameter, CategoricalHyperparameter) and\
                    isinstance(fpair[1].hyperparameter, CategoricalHyperparameter):
                forbidden += '\n(' + fpair[0].hyperparameter.name + ' == ' + f'\"{fpair[0].value}\") ' +\
                    '& (' + fpair[1].hyperparameter.name + ' == ' + f'\"{fpair[1].value}\")'
            elif isinstance(fpair[0].hyperparameter, CategoricalHyperparameter):
                forbidden += '\n(' + fpair[0].hyperparameter.name + ' == ' + f'\"{fpair[0].value}\") ' +\
                    '& (' + fpair[1].hyperparameter.name + ' == ' + f'{fpair[1].value})'
            elif isinstance(fpair[1].hyperparameter, CategoricalHyperparameter):
                forbidden += '\n(' + fpair[0].hyperparameter.name + ' == ' + f'{fpair[0].value}) ' +\
                    '& (' + fpair[1].hyperparameter.name + ' == ' + f'\"{fpair[1].value}\")'

        forbidden += '\n'

        with open("forbidden.txt", "w") as text_file:
            text_file.write(forbidden)

        self.irace_param_space = irace_param_space

        return default_conf

    def get_ps_oat(self, param_space):
        '''
        OAT does not handle forbidden parameter value combinations.
        OAT can handle multiple parent and 1 child conditionals,
        but not one parent multiple children conditionals.
        We naively just take the first one in the list.
        OAT does not support conditionals that are conditional.
        We leave them out naively.
        Oat does not support conditionals with value ranges.
        We naively only use the first value.

        Note: Although this is suboptimal, invalid configurations will
        lead to crah or bad results such that OAT will rate them
        as subpar.
        '''

        param_file = '<?xml version="1.0" encoding="utf-8" ?>\n'
        param_file += '<node xsi:type="and" xsi:noNamespaceSchemaLocation="../parameterTree.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'

        conditional_params = param_space.get_all_conditional_hyperparameters()

        hyperparameters = param_space.get_hyperparameters()
        to_set = []
        for hp in hyperparameters:
            to_set.append(hp.name)
        params_dict = param_space.get_hyperparameters_dict()

        conditions = param_space.get_conditions()

        parents = {}
        for cond in conditions:
            if not isinstance(cond, AndConjunction):
                if cond.parent.name not in parents:
                    parents[cond.parent.name] = {cond.child.name: [cond.value, cond.child]}
                else:
                    parents[cond.parent.name][cond.child.name] = [cond.value, cond.child]
            else:
                for c in cond.components:
                    if c.parent.name not in parents:
                        parents[c.parent.name] = {c.child.name: [c.value, c.child]}
                    else:
                        parents[c.parent.name][c.child.name] = [c.value, c.child]

        print(parents)

        def set_conditionals(children, param_file, to_set, parents, tab=''):
            for child, value in children.items():
                if child in to_set:
                    if isinstance(value[0], list):
                        value[0] = value[0][0]
                    param_file += f'{tab}\t\t<choice>\n'
                    param_file += f'{tab}\t\t\t<string>{value[0]}</string>\n'
                    param_file += f'{tab}\t\t\t<child xsi:type="value" id="{child}">\n'
                    if isinstance(value[1], CategoricalHyperparameter):
                        choices = ''
                        for c in value[1].choices:
                            choices += f'{c} '
                        param_file += f'{tab}\t\t\t\t<domain xsi:type="categorical" strings="{choices[:-1]}" defaultIndexOrValue="{value[1].choices.index(value[1].default_value)}"/>\n'
                        param_file += f'{tab}\t\t\t</child>\n'
                        param_file += f'{tab}\t\t</choice>\n'
                    elif isinstance(value[1], UniformIntegerHyperparameter):
                        if value[1].lower < -2147483647:
                            lower = -2147483647
                        else:
                            lower = value[1].lower
                        if value[1].upper > 2147483647:
                            upper = 2147483647
                        else:
                            upper = value[1].upper
                        param_file += f'{tab}\t\t\t\t<domain xsi:type="discrete" start="{lower}" end="{upper}" defaultIndexOrValue="{value[1].default_value}"/>\n'
                        param_file += f'{tab}\t\t\t</child>\n'
                        param_file += f'{tab}\t\t</choice>\n'
                    elif isinstance(value[1], UniformFloatHyperparameter):
                        param_file += f'{tab}\t\t\t\t<domain xsi:type="continuous" start="{value[1].lower}" end="{value[1].upper}" defaultIndexOrValue="{value[1].default_value}"/>\n'
                        param_file += f'{tab}\t\t\t</child>\n'
                        param_file += f'{tab}\t\t</choice>\n'

                    to_set.remove(child)              

            return param_file, to_set

        for param in hyperparameters:
            if param.name in to_set:
                if param.name in parents and parents[param.name].keys() in to_set:
                    param_file += f'\t<node xsi:type="or" id="{param.name}">\n'
                    if isinstance(param, CategoricalHyperparameter):
                        choices = ''
                        for c in param.choices:
                            choices += f'{c} '
                        param_file += f'\t\t<domain xsi:type="categorical" strings="{choices[:-1]}" defaultIndexOrValue="{param.choices.index(param.default_value)}"/>\n'

                        children = parents[param.name]
                        param_file, to_set = set_conditionals(children, param_file, to_set, parents)
                        param_file += '\t</node>\n'
                        

                    elif isinstance(param, UniformIntegerHyperparameter):
                        if param.lower < -2147483647:
                            lower = -2147483647
                        else:
                            lower = param.lower
                        if param.upper > 2147483647:
                            upper = 2147483647
                        else:
                            upper = param.upper
                        param_file += f'  <domain xsi:type="discrete" start="{lower}" end="{upper}" defaultIndexOrValue="{param.default_value}"/>\n'

                        children = parents[param.name]
                        param_file, to_set = set_conditionals(children, param_file, to_set, parents)
                        param_file += '\t</node>\n'

                    elif isinstance(param, UniformFloatHyperparameter):
                        param_file += f'\t\t<domain xsi:type="continuous" start="{param.lower}" end="{param.upper}" defaultIndexOrValue="{param.default_value}"/>\n'
                        
                        children = parents[param.name]
                        param_file, to_set = set_conditionals(children, param_file, to_set, parents)
                        param_file += '\t</node>\n'
                else:
                    param_file += f'\t<node xsi:type="value" id="{param.name}">\n'
                    if isinstance(param, CategoricalHyperparameter):
                        choices = ''
                        for c in param.choices:
                            choices += f'{c} '
                        param_file += f'\t\t<domain xsi:type="categorical" strings="{choices[:-1]}" defaultIndexOrValue="{param.choices.index(param.default_value)}"/>\n'
                        param_file += '\t</node>\n'
                    elif isinstance(param, UniformIntegerHyperparameter):
                        if param.lower < -2147483647:
                            lower = -2147483647
                        else:
                            lower = param.lower
                        if param.upper > 2147483647:
                            upper = 2147483647
                        else:
                            upper = param.upper
                        param_file += f'\t\t<domain xsi:type="discrete" start="{lower}" end="{upper}" defaultIndexOrValue="{param.default_value}"/>\n'
                        param_file += '\t</node>\n'
                    elif isinstance(param, UniformFloatHyperparameter):
                        param_file += f'\t\t<domain xsi:type="continuous" start="{param.lower}" end="{param.upper}" defaultIndexOrValue="{param.default_value}"/>\n'
                        param_file += '\t</node>\n'

                to_set.remove(param.name)

        param_file += '</node>\n'

        return param_file

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

    def run_engine_config(self, ac_tool, config, metric, engine, plantype, problem, gray_box_listener=None):
        """Execute configurated engine run.

        paremer config: configuration of engine.
        parameter engine: str, engine name.
        parameter plantype: str, type of planning.

        return feedback: result from configurated engine run.
        """
        if plantype == 'OneshotPlanner':
            config = self.transform_conf_from_ac(ac_tool, engine, config)
            if gray_box_listener is not None:
                with OneshotPlanner(name=engine,
                                    params=config,
                                    output_stream=gray_box_listener) as planner:
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
            else:
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

        elif plantype == 'AnytimePlanner':
            config = self.transform_conf_from_ac(ac_tool, engine, config)
            if gray_box_listener is not None:
                with AnytimePlanner(name=engine,
                                    params=config,
                                    output_stream=gray_box_listener) as planner:
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
            else:
                with AnytimePlanner(name=engine,
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
