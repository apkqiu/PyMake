try:
    from .builder_main import main
except ImportError:
    import sys
    raise EnvironmentError(f'Please use "{sys.executable} -m builder" instead.')

main()