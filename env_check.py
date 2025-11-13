import sys
print('CWD:', __import__('os').getcwd())
print('PYTHON:', sys.executable)
print('VERSION:', sys.version)
try:
    import PIL
    print('PILLOW:', PIL.__version__)
except Exception as e:
    print('PILLOW_MISSING:', e)
