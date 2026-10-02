# Check exact ParCorr import
import tigramite.independence_tests as it
print("Available:", [x for x in dir(it) if 'ar' in x.lower() or 'corr' in x.lower()])
