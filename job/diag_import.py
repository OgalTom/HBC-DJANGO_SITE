import importlib, traceback

try:
    m = importlib.import_module('client.models')
    names = [n for n in ('User','Job','Application','Transaction') if hasattr(m, n)]
    print('Imported client.models; found:', names)
except Exception:
    traceback.print_exc()
