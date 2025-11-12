import csv
from django.contrib.auth import get_user_model
from .models import Voter

User = get_user_model()


def import_voters_from_file(fileobj, create_users=False, default_password=None):
    """Import voters from a file-like object (CSV). Returns a summary dict.

    Expected CSV headers: username, control_number, email, password
    """
    reader = csv.DictReader((line.decode('utf-8') if isinstance(line, bytes) else line) for line in fileobj)
    created = 0
    skipped = 0
    updated = 0
    messages = []
    for row in reader:
        username = (row.get('username') or '').strip()
        control = (row.get('control_number') or '').strip()
        email = (row.get('email') or '').strip()
        password = (row.get('password') or '').strip() or default_password
        if not control:
            messages.append(('warning', f'Skipping row without control_number: {row}'))
            skipped += 1
            continue
        user = None
        if username:
            user = User.objects.filter(username=username).first()
        if not user and email:
            user = User.objects.filter(email=email).first()
        if not user and create_users:
            # ensure username uses control number for created users
            username = control
            user = User.objects.create_user(username=username, email=email)
            if password:
                user.set_password(password)
                user.save()
            messages.append(('success', f'Created User {user.username}'))
        # enforce control_number as username for the resolved user (may update existing users)
        if user:
            desired_username = control
            if user.username != desired_username:
                user.username = desired_username
                user.save(update_fields=['username'])
        if not user:
            messages.append(('warning', f'No User found for control {control}; use create_users to create. Skipping'))
            skipped += 1
            continue
        voter, created_flag = Voter.objects.get_or_create(user=user, defaults={'control_number': control, 'is_eligible': True})
        if created_flag:
            created += 1
            messages.append(('success', f'Created Voter for user {user.username} control {control}'))
        else:
            if voter.control_number != control:
                voter.control_number = control
                voter.save(update_fields=['control_number'])
                updated += 1
                messages.append(('success', f'Updated Voter {user.username} control to {control}'))
            else:
                messages.append(('info', f'Existing Voter {user.username} - skipped'))
                skipped += 1
    return {'created': created, 'updated': updated, 'skipped': skipped, 'messages': messages}
