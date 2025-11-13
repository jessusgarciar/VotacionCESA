import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','VotacionCESA.settings')
# Ensure the project package directory is on sys.path when running from the repo root
proj_dir = os.path.dirname(__file__)
candidate = os.path.join(proj_dir, 'VotacionCESA')
if candidate not in sys.path:
    sys.path.insert(0, candidate)
import django
django.setup()
from django.urls import get_resolver
r = get_resolver(None)
for p in r.url_patterns:
    try:
        pat = p.pattern.describe()
    except Exception:
        pat = str(p.pattern)
    print(type(p).__name__, pat, getattr(p,'name',None))
