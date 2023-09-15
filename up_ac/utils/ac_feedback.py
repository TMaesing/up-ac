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
            if 'Plan quality' in line:
                line = line.split(' ')
                for fb in line:
                    if '.' in fb:
                        feedback = float(fb)

    elif engine == 'fast-downward':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if 'Plan cost' in line:
                line = line.split(' ')
                feedback = float(line[5])

    elif engine == 'enhsp':
        output = result.log_messages[0].message.split('\n')
        for line in output:
            if 'Metric' in line:
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
            if 'Duration:' in line:
                line = line.split(' ')
                feedback = float(line[-1])

    elif engine == 'fast-downward':
        output = result.log_messages[0].message
        output = output.split('\n')
        for line in output:
            if 'Planner time:' in line:
                feedback = float(line.split(' ')[-1][:-1])

    elif engine == 'pyperplan':
        feedback = 'measure'

    elif engine == 'tamer':
        feedback = 'measure'

    elif engine == 'enhsp':
        output = result.log_messages[0].message.split('\n')
        for line in output:
            if 'Planning Time' in line:
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
