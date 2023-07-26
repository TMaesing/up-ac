"""Functions to transform feedback from engines."""


def qaul_feedback(engine, result):
    """Transform/parse specific solution quality engine output.

    parameter engine: str, name of engine.
    parameter result: object, planning result.
    """
    feedback = None
    if engine == 'lpg':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if line[:12] == 'Plan quality':
                line = line.split(' ')
                feedback = float(line[5])

    elif engine == 'fast-downward':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if line[26:35] == 'Plan cost':
                line = line.split(' ')
                feedback = float(line[5])

    elif engine == 'pyperplan':
        # TODO
        feedback = 1.0

    elif engine == 'tamer':
        # TODO
        feedback = 1.0

    elif engine == 'enhsp':
        output = result.log_messages[0].message.split('\n')
        for line in output:
            if line[:6] == 'Metric':
                line = line.split(':')
                feedback = float(line[1])

    elif engine == 'fmap':
        # TODO
        feedback = 1.0

    return feedback


def runtime_feedback(engine, result):
    """Transform/parse specific solution quality engine output.

    parameter engine: str, name of engine.
    parameter result: object, planning result.
    """
    feedback = None
    if engine == 'lpg':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if line[:8] == 'Duration':
                line = line.split(' ')
                feedback = float(line[-1])

    elif engine == 'fast-downward':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if line[26:36] == 'Total time':
                line = line.split(' ')
                feedback = float(line[5][:-1])

    elif engine == 'pyperplan':
        # TODO -> get output from pyperplan
        feedback = 1.0

    elif engine == 'tamer':
        # TODO -> get output from pyperplan
        feedback = 1.0

    elif engine == 'enhsp':
        output = result.log_messages[0].message.split('\n')
        for line in output:
            if line[:13] == 'Planning Time':
                line = line.split(':')
                feedback = (float(line[1])) / 100

    elif engine == 'fmap':
        # TODO -> get output from pyperplan
        feedback = 1.0

    return feedback


def gray_box_feedback(engine, result):
    """Transform/parse specific solution quality engine output.

    parameter engine: str, name of engine.
    parameter result: object, planning result.
    """
    # TODO
    if engine == 'lpg':
        feedback = None

    elif engine == 'fast-downward':
        feedback = None

    return feedback
