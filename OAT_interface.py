"""OAT algorithm configuration interface for unified planning."""
from AC_interface import GenericACInterface


class GenericACInterface(GenericACInterface):
    """OAT AC interface."""

    def __init__(self):
        """Initialize OAT interface."""
        GenericACInterface.__init__(self)

    def transform_conf_from_ac(self, ac_tool, engine, configuration):
        """Transform configuration to up engine format.

        parameter ac_tool: str, name of AC tool in use.
        parameter engines: list of str, names of engines.
        parameter configuration: dict, parameter names with values.

        return config: dict, configuration.
        """
        config = configuration

        return config

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
