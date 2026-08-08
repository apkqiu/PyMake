trace_types = {}


def define_tracer(type):
    def wrapper(f):
        trace_types[type] = f
        return f

    return wrapper


def trace(type: str, file: str):
    deps = trace_types.get(type, lambda x: [])(file)
    # place_data(file, {"deps": deps})
    return deps

