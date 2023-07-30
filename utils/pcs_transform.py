"""Functions to transform pcs for engines."""


def transform_pcs(engine, configuration):
    """Transform specific engine output to.

    parameter engine: str, name of engine.
    parameter configuration: pcs object, configuration as pcs.
    """
    config = {}

    if engine == 'lpg':
        for c in configuration.keys():
            config['-' + c] = str(configuration[c])

    elif engine == 'fast-downward' or \
            engine == 'pyperplan' or \
            engine == 'symk':
        for c in configuration.keys():
            config[c] = str(configuration[c])

    elif engine == 'tamer':
        for c in configuration.keys():
            config[c] = configuration[c]

    elif engine == 'enhsp':
        for c in configuration.keys():
            config[c] = configuration[c]

    elif engine == 'fmap':
        for c in configuration.keys():
            config[c] = configuration[c]

    return config


def transform_from_oat(engine, configuration):
    """Transform specific engine output to.

    parameter engine: str, name of engine.
    parameter configuration: pcs object, configuration as pcs.
    """
    # TODO
    config = {}

    return config
