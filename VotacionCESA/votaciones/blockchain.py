"""Algorand registration checker.

This module implements a real check to determine whether an Algorand address
is registered/opted-in to the voting smart contract (application). It prefers
to use the Algod client (algosdk). Configuration is read from Django settings:

- ALGOD_ADDRESS, ALGOD_TOKEN, ALGOD_HEADERS (for Algod client)
- ALGORAND_APP_ID (or ALGOD_APP_ID / ALGORAND_CONTRACT_APP_ID)
- DEBUG and BLOCKCHAIN_REGISTERED_ADDRESSES are honored for development/testing

If the Algod client or settings are missing, the function raises RuntimeError so
callers can deny access (authentication backend treats exceptions as failures).
"""
from django.conf import settings


def _get_app_id():
    app_id = getattr(settings, 'ALGORAND_APP_ID', None)
    if app_id is None:
        app_id = getattr(settings, 'ALGOD_APP_ID', None)
    if app_id is None:
        app_id = getattr(settings, 'ALGORAND_CONTRACT_APP_ID', None)
    if app_id is None:
        return None
    try:
        return int(app_id)
    except Exception:
        return None


def is_address_registered(address: str) -> bool:
    """Return True when the given address is registered/opted-in to the voting app.

    Raises RuntimeError on configuration/import/network errors so the caller can
    treat the verification as failed.
    """
    if not address:
        return False

    # In DEBUG mode allow testing unless a specific whitelist is provided
    if getattr(settings, 'DEBUG', False):
        whitelist = getattr(settings, 'BLOCKCHAIN_REGISTERED_ADDRESSES', None)
        if isinstance(whitelist, (list, tuple)) and len(whitelist) > 0:
            return address in whitelist
        return True

    app_id = _get_app_id()
    if app_id is None:
        raise RuntimeError('ALGORAND_APP_ID not configured')

    try:
        from algosdk.v2client import algod
    except Exception as e:
        raise RuntimeError('algosdk is required for blockchain verification: ' + str(e))

    algod_address = getattr(settings, 'ALGOD_ADDRESS', None) or getattr(settings, 'ALGORAND_ALGOD_ADDRESS', None)
    algod_token = getattr(settings, 'ALGOD_TOKEN', None) or getattr(settings, 'ALGORAND_ALGOD_TOKEN', None)
    algod_headers = getattr(settings, 'ALGOD_HEADERS', None)

    if not algod_address:
        raise RuntimeError('ALGOD_ADDRESS not configured in settings')

    try:
        client = algod.AlgodClient(algod_token or '', algod_address, headers=algod_headers)
    except Exception as e:
        raise RuntimeError('Could not create Algod client: ' + str(e))

    try:
        acct_info = client.account_info(address)
    except Exception as e:
        raise RuntimeError('Error fetching account info from Algod: ' + str(e))

    apps_local = acct_info.get('apps-local-state', []) or []
    for entry in apps_local:
        if entry.get('id') == app_id:
            return True

    return False
