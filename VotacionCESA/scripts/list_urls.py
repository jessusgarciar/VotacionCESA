from django import setup
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','VotacionCESA.settings')
setup()
from django.urls import get_resolver
r = get_resolver(None)
for p in r.url_patterns:
    try:
        pat = p.pattern.describe()
    except Exception:
        pat = str(p.pattern)
    print(type(p).__name__, pat, getattr(p,'name',None))
