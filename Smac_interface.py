"""Smac algorithm configuration interface for unified planning."""
from AC_interface import GenericACInterface

class SmacInterface(GenericACInterface):
    """Generic Smac interface."""

    def __init__(self):
        """Initialize Smac interface."""
        GenericACInterface.__init__(self)

    def transform_conf_from_ac(self, ac_tool, engine, configuration):
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

    def transform_param_space(self, ac_tool, pcs):
        """Transform configuration to AC tool format.

        parameter pcs: ConfigSpace object, parameter space.
        parameter ac_tool: str, AC tool in use.

        return param_space: transformed parameter space.
        """
        if ac_tool == 'SMAC':  # SMAC uses ConfigSpace
            param_space = pcs

        return param_space
