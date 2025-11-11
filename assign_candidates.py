import os
import sys
# make sure project root is on path
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE','VotacionCESA.settings')
import django
django.setup()
from votaciones.models import Candidate, Election
from django.utils import timezone

latest = Election.objects.order_by('-start_date').first()
if not latest:
    print('No election found. Create an Election first in admin.')
    sys.exit(1)

qs = Candidate.objects.filter(election__isnull=True)
print(f"Assigning {qs.count()} candidates to Election {latest.id} - {latest.name}")
for c in qs:
    c.election = latest
    c.save(update_fields=['election'])
    print('Assigned:', c.id, c.name)

print('Done')
