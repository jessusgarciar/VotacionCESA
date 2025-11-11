"""Minimal integration layer with Algorand.

This module provides a small, testable interface used by the app. It attempts to use
`algosdk` when available and falls back to a local simulation (UUID) if not.

Configuration expected via Django settings or environment variables:
 - ALGOD_ADDRESS
 - ALGOD_TOKEN
 - ALGOD_HEADERS (optional)
 - ALGORAND_SENDER_MNEMONIC (or ALGORAND_SENDER_ADDRESS + ALGORAND_SENDER_PRIVATE_KEY)

Note: this file deliberately keeps operations simple and synchronous. For production
you'll want proper key management, secure storage, retries and asynchronous handling.
"""
from typing import Optional
import os
import json
import time
import uuid

try:
    from algosdk.v2client import algod
    from algosdk import account, transaction
    from algosdk import mnemonic as algo_mnemonic
    ALGOSDK_AVAILABLE = True
except Exception:
    ALGOSDK_AVAILABLE = False

from django.conf import settings


def _simulate_send(note_bytes: bytes) -> str:
    """Fallback simulation that returns a uuid as txid."""
    return str(uuid.uuid4())


def send_vote_tx(election_id: int, candidate_id: int, note: Optional[bytes] = None, wait_for_confirmation: bool = True) -> str:
    """Send a vote representation to Algorand and return txid.

    The transaction note should NOT include voter-identifying information.
    If Algorand SDK is not configured, this will simulate and return a UUID.
    """
    note = note or json.dumps({'election_id': election_id, 'candidate_id': candidate_id}).encode('utf-8')

    # If algosdk isn't installed or settings not provided, simulate
    if not ALGOSDK_AVAILABLE:
        return _simulate_send(note)

    algod_address = getattr(settings, 'ALGOD_ADDRESS', os.environ.get('ALGOD_ADDRESS'))
    algod_token = getattr(settings, 'ALGOD_TOKEN', os.environ.get('ALGOD_TOKEN'))
    algod_headers = getattr(settings, 'ALGOD_HEADERS', None)

    if not algod_address or not algod_token:
        # missing config — simulate
        return _simulate_send(note)

    client = algod.AlgodClient(algod_token, algod_address, headers=algod_headers)

    # Sender credentials (mnemonic) — prefer settings, then env
    sender_mnemonic = getattr(settings, 'ALGORAND_SENDER_MNEMONIC', os.environ.get('ALGORAND_SENDER_MNEMONIC'))
    if sender_mnemonic:
        sender_private_key = algo_mnemonic.to_private_key(sender_mnemonic)
        sender_address = algo_mnemonic.to_public_key(sender_mnemonic)
    else:
        # allow explicit key pair via env (not recommended)
        sender_address = os.environ.get('ALGORAND_SENDER_ADDRESS')
        sender_private_key = os.environ.get('ALGORAND_SENDER_PRIVATE_KEY')

    if not sender_address or not sender_private_key:
        # No credentials available — simulate
        return _simulate_send(note)

    # Build a minimal payment transaction with zero value and note payload
    params = client.suggested_params()
    unsigned_txn = transaction.PaymentTxn(sender_address, params, sender_address, 0, None, note=note)
    signed_txn = unsigned_txn.sign(sender_private_key)

    txid = client.send_transaction(signed_txn)

    if wait_for_confirmation:
        _wait_for_confirmation(client, txid)

    return txid


def _wait_for_confirmation(client: 'algod.AlgodClient', txid: str, timeout: int = 10):
    """Wait for a transaction to be confirmed. Raises on timeout."""
    start = time.time()
    while True:
        try:
            pending = client.pending_transaction_info(txid)
            if pending.get('confirmed-round', 0) > 0:
                return pending
        except Exception:
            # continue trying until timeout
            pass
        if time.time() - start > timeout:
            raise TimeoutError(f"tx {txid} not confirmed after {timeout}s")
        time.sleep(1)
