import importlib, traceback, inspect

try:
    m = importlib.import_module('client.models')
    print('module file:', getattr(m, '__file__', None))
    keys = [k for k in m.__dict__.keys() if not k.startswith('_')]
    print('defined names count:', len(keys))
    print('some keys:', keys[:50])
    try:
        src = inspect.getsource(m)
        print('\n--- source snippet ---\n')
        print('\n'.join(src.splitlines()[:80]))
    except Exception as e:
        print('could not read source:', e)
except Exception:
    traceback.print_exc()
