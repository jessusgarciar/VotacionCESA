from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
import tempfile
import os

from ..models import Voter

User = get_user_model()


class ImportVotersCommandTest(TestCase):
    def test_import_creates_voters(self):
        # create existing user
        existing = User.objects.create_user(username='existing', password='x')
        csv_content = "username,control_number,email,password\n"
        csv_content += f"existing,CTRL123,existing@example.com,\n"
        csv_content += f"newuser,CTRL456,new@example.com,pass123\n"
        fd, path = tempfile.mkstemp(suffix='.csv', text=True)
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        try:
            call_command('import_voters', path, '--create-users')
            self.assertTrue(Voter.objects.filter(user=existing, control_number='CTRL123').exists())
            self.assertTrue(Voter.objects.filter(user__username='newuser', control_number='CTRL456').exists())
        finally:
            os.remove(path)
