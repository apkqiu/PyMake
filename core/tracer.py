tracers = {}


def define_tracer(name):
    def wrapper(f):
        tracers[name] = f
        return f
    return wrapper


def get_tracer(name: str):
    # place_data(file, {"deps": deps})
    return tracers.get(name, lambda x: [])
