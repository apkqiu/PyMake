trace_types = {}


def define_tracer(type):
    def wrapper(f):
        trace_types[type] = f
        return f

    return wrapper


def get_tracer(type: str):
    # place_data(file, {"deps": deps})
    return trace_types.get(type, lambda x: [])
