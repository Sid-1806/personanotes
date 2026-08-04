import os
import sys

# Ensure the backend root is on sys.path so `import app...` resolves when
# pytest collects tests from the tests/ directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
