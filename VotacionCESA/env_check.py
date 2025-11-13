import sys
import os
print('CWD:', os.getcwd())
print('PYTHON:', sys.executable)
print('VERSION:', sys.version)
try:
    import PIL
    print('PILLOW:', PIL.__version__)
except Exception as e:
    print('PILLOW_MISSING:', e)
