import importlib, traceback

try:
    m = importlib.import_module('client.models')
    print('Imported client.models; attributes:', [n for n in dir(m) if not n.startswith('_')])
except Exception:
    traceback.print_exc()
