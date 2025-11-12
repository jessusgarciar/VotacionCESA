from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
import logging

from .models import Voter
from .blockchain import is_address_registered

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class ControlNumberBackend(ModelBackend):
    """Authenticate using username/password or control_number/password.

    If 'username' supplied is not a username but matches a Voter.control_number,
    the associated User will be used for authentication.
    When `settings.REQUIRE_BLOCKCHAIN_REGISTRATION` is True, the backend will
    require that the related `Voter.blockchain_address` is present and that
    `is_address_registered` returns True before allowing authentication.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try normal username first
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            user = None

        voter = None
        if user is None:
            # try to find a Voter with control_number
            try:
                voter = Voter.objects.select_related('user').get(control_number=username)
                user = voter.user
            except Voter.DoesNotExist:
                return None

        # Verify password and standard auth checks first
        if not (user.check_password(password) and self.user_can_authenticate(user)):
            return None

        # If blockchain registration is required, enforce it
        if getattr(settings, 'REQUIRE_BLOCKCHAIN_REGISTRATION', False):
            # ensure we have a Voter instance
            if voter is None:
                try:
                    voter = Voter.objects.select_related('user').get(user=user)
                except Voter.DoesNotExist:
                    logger.warning('User %s attempted login but no Voter record exists.', getattr(user, 'username', None))
                    return None

            address = (voter.blockchain_address or '').strip()
            if not address:
                logger.info('Denying login for user %s: no blockchain_address on Voter.', getattr(user, 'username', None))
                return None

            try:
                registered = is_address_registered(address)
            except RuntimeError as exc:
                # Treat inability to verify as denial; log for operator action.
                logger.exception('Error while checking blockchain registration for address %s: %s', address, exc)
                return None

            if not registered:
                logger.info('Denying login for user %s: address %s is not registered/opted-in.', getattr(user, 'username', None), address)
                return None

        # All checks passed
        return user
