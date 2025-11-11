"""Reader utilities to fetch on-chain vote counts from Algorand Indexer.

This module attempts to use an Algorand Indexer (if configured) to retrieve
transactions that contain vote notes (the same format used when sending votes).
If the indexer is not configured or unavailable, functions return None so callers
can fallback to local `OnChainRecord` data.

Notes:
- Expects INDEXER_ADDRESS and INDEXER_TOKEN in Django settings or environment.
"""
from typing import Optional, Dict
import os
import json

try:
    from algosdk.v2client import indexer
    ALGOSDK_INDEXER = True
except Exception:
    ALGOSDK_INDEXER = False

from django.conf import settings
from .models import Candidate, Election


def _decode_note(note_b64: str) -> Optional[dict]:
    try:
        import base64
        b = base64.b64decode(note_b64)
        return json.loads(b.decode('utf-8'))
    except Exception:
        return None


def get_counts_from_indexer(election_id: int) -> Optional[Dict[int, int]]:
    """Return a mapping candidate_id -> count for a given election from the indexer.

    Returns None if indexer not configured or an error occurs.
    """
    if not ALGOSDK_INDEXER:
        return None

    indexer_address = getattr(settings, 'INDEXER_ADDRESS', os.environ.get('INDEXER_ADDRESS'))
    indexer_token = getattr(settings, 'INDEXER_TOKEN', os.environ.get('INDEXER_TOKEN'))
    if not indexer_address or not indexer_token:
        return None

    try:
        client = indexer.IndexerClient(indexer_token, indexer_address)
        # Basic approach: search transactions with note-prefix that include the election_id
        # Note: this is a heuristic and depends on how notes were encoded.
        # We perform a transactions search and decode notes that parse as JSON.
        response = client.search_transactions(limit=1000)
        counts = {}
        txs = response.get('transactions', [])
        for tx in txs:
            note_b64 = tx.get('note')
            if not note_b64:
                continue
            decoded = _decode_note(note_b64)
            if not decoded:
                continue
            if decoded.get('election_id') == election_id:
                cid = decoded.get('candidate_id')
                if cid:
                    counts[cid] = counts.get(cid, 0) + 1
        return counts
    except Exception:
        return None


def get_counts_for_election(election: Election) -> Optional[Dict[int, int]]:
    if not election:
        return None
    return get_counts_from_indexer(election.id)
