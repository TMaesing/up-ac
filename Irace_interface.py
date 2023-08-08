"""Irace algorithm configuration interface for unified planning."""
import pandas as pd
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri

from AC_interface import GenericACInterface
from utils.pcs_transform import transform_pcs

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


class IraceInterface(GenericACInterface):
    """Irace AC interface."""

    def __init__(self):
        """Initialize Irace interface."""
        GenericACInterface.__init__(self)

    def transform_conf_from_ac(self, engine, configuration):
        """Transform configuration to up engine format.

        parameter ac_tool: str, name of AC tool in use.
        parameter engines: list of str, names of engines.
        parameter configuration: dict, parameter names with values.

        return config: dict, configuration.
        """
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

        if len(forbidden) > 2:
            forbiddens = True
        else:
            forbiddens = False

        with open("forbidden.txt", "w") as text_file:
            text_file.write(forbidden)

        self.irace_param_space = irace_param_space

        return default_conf, forbiddens
