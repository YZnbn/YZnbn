import tigramite.independence_tests as it
import os
mod_dir = os.path.dirname(it.__file__)
print("Module dir:", mod_dir)
for f in os.listdir(mod_dir):
    if f.endswith('.py') and not f.startswith('_'):
        print("  ", f)
