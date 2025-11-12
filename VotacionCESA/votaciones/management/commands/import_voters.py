from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from votaciones.utils import import_voters_from_file
import os


class Command(BaseCommand):
    help = 'Import voters from a CSV file. Expected columns: username,control_number,email,password (password optional).'

    def add_arguments(self, parser):
        parser.add_argument('csvfile', type=str)
        parser.add_argument('--create-users', action='store_true', help='Create User objects if username not found.')
        parser.add_argument('--password', type=str, help='Default password for created users (optional).')

    def handle(self, *args, **options):
        path = options['csvfile']
        create_users = options.get('create_users', False)
        default_password = options.get('password')
        if not os.path.exists(path):
            raise CommandError(f'File not found: {path}')

        with open(path, 'rb') as fh:
            summary = import_voters_from_file(fh, create_users=create_users, default_password=default_password)

        for level, msg in summary.get('messages', []):
            if level == 'success':
                self.stdout.write(self.style.SUCCESS(msg))
            elif level == 'warning':
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(msg)

        self.stdout.write(self.style.SUCCESS(f"Import completed: created={summary['created']} updated={summary['updated']} skipped={summary['skipped']}"))
