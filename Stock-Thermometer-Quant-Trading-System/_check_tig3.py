# Check tigramite imports
try:
    from tigramite import data_processing
    print("data_processing: OK")
except Exception as e:
    print(f"data_processing: {e}")

try:
    from tigramite.pcmci import PCMCI
    print("pcmci.PCMCI: OK")
except Exception as e:
    print(f"pcmci.PCMCI: {e}")

try:
    from tigramite.independence_tests import ParCorr
    print("independence_tests.ParCorr: OK")
except Exception as e:
    print(f"independence_tests.ParCorr: {e}")

# List what's available
import tigramite
print("\nSubmodules:", [x for x in dir(tigramite) if not x.startswith('_')])
