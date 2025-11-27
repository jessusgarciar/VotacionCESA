"""Smart Contract integration for Algorand voting app.

This module provides functions to interact with the voting smart contract:
- Deploy the application
- Register voters (OptIn)
- Submit votes (ApplicationCall)
- Read vote data

Configuration expected via Django settings or environment variables:
 - ALGOD_ADDRESS
 - ALGOD_TOKEN
 - ALGOD_HEADERS (optional)
 - ALGORAND_APP_ID (after deployment)
 - ALGORAND_CREATOR_MNEMONIC (for deployment only)
"""
from typing import Optional, Dict
import os
import base64
import time

try:
    from algosdk.v2client import algod
    from algosdk import account, transaction
    from algosdk import mnemonic as algo_mnemonic
    ALGOSDK_AVAILABLE = True
except Exception:
    ALGOSDK_AVAILABLE = False

from django.conf import settings


def _get_algod_client():
    """Get configured Algod client or None if not available."""
    if not ALGOSDK_AVAILABLE:
        return None
    
    algod_address = getattr(settings, 'ALGOD_ADDRESS', os.environ.get('ALGOD_ADDRESS'))
    algod_token = getattr(settings, 'ALGOD_TOKEN', os.environ.get('ALGOD_TOKEN'))
    algod_headers = getattr(settings, 'ALGOD_HEADERS', None)
    
    if not algod_address or not algod_token:
        return None
    
    return algod.AlgodClient(algod_token, algod_address, headers=algod_headers)


def _wait_for_confirmation(client: 'algod.AlgodClient', txid: str, timeout: int = 10):
    """Wait for a transaction to be confirmed."""
    start = time.time()
    while True:
        try:
            pending = client.pending_transaction_info(txid)
            if pending.get('confirmed-round', 0) > 0:
                return pending
        except Exception:
            pass
        if time.time() - start > timeout:
            raise TimeoutError(f"tx {txid} not confirmed after {timeout}s")
        time.sleep(1)


def compile_program(client, source_code):
    """Compile TEAL source code."""
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])


def create_voting_app(
    creator_mnemonic: str,
    reg_begin: int,
    reg_end: int,
    vote_begin: int,
    vote_end: int,
    approval_teal_path: str = "approval.teal",
    clear_teal_path: str = "clear.teal"
) -> Optional[int]:
    """
    Deploy the voting application to Algorand.
    
    Args:
        creator_mnemonic: Mnemonic of the account creating the app
        reg_begin: Registration start timestamp (Unix)
        reg_end: Registration end timestamp (Unix)
        vote_begin: Voting start timestamp (Unix)
        vote_end: Voting end timestamp (Unix)
        approval_teal_path: Path to approval.teal file
        clear_teal_path: Path to clear.teal file
    
    Returns:
        Application ID if successful, None otherwise
    """
    client = _get_algod_client()
    if not client:
        print("Algod client not available")
        return None
    
    # Get creator credentials
    creator_private_key = algo_mnemonic.to_private_key(creator_mnemonic)
    creator_address = algo_mnemonic.to_public_key(creator_mnemonic)
    
    # Read and compile TEAL programs
    with open(approval_teal_path, "r") as f:
        approval_source = f.read()
    with open(clear_teal_path, "r") as f:
        clear_source = f.read()
    
    approval_program = compile_program(client, approval_source)
    clear_program = compile_program(client, clear_source)
    
    # Define schema
    global_schema = transaction.StateSchema(num_uints=5, num_byte_slices=1)  # Creator + 4 timestamps
    local_schema = transaction.StateSchema(num_uints=2, num_byte_slices=0)   # Voted + CandidateID
    
    # Get suggested params
    params = client.suggested_params()
    
    # Create application args (timestamps)
    app_args = [
        reg_begin.to_bytes(8, 'big'),
        reg_end.to_bytes(8, 'big'),
        vote_begin.to_bytes(8, 'big'),
        vote_end.to_bytes(8, 'big')
    ]
    
    # Create unsigned transaction
    txn = transaction.ApplicationCreateTxn(
        sender=creator_address,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=app_args
    )
    
    # Sign transaction
    signed_txn = txn.sign(creator_private_key)
    
    # Send transaction
    txid = client.send_transaction(signed_txn)
    print(f"Transaction sent with ID: {txid}")
    
    # Wait for confirmation
    confirmed_txn = _wait_for_confirmation(client, txid)
    
    # Get application ID
    app_id = confirmed_txn.get('application-index')
    print(f"Application created with ID: {app_id}")
    
    return app_id


def voter_optin(voter_mnemonic: str, app_id: int) -> Optional[str]:
    """
    Register a voter by opting into the application.
    
    Args:
        voter_mnemonic: Mnemonic of the voter account
        app_id: Application ID
    
    Returns:
        Transaction ID if successful, None otherwise
    """
    client = _get_algod_client()
    if not client:
        print("Algod client not available")
        return None
    
    # Get voter credentials
    voter_private_key = algo_mnemonic.to_private_key(voter_mnemonic)
    voter_address = algo_mnemonic.to_public_key(voter_mnemonic)
    
    # Get suggested params
    params = client.suggested_params()
    
    # Create opt-in transaction
    txn = transaction.ApplicationOptInTxn(
        sender=voter_address,
        sp=params,
        index=app_id
    )
    
    # Sign and send
    signed_txn = txn.sign(voter_private_key)
    txid = client.send_transaction(signed_txn)
    
    # Wait for confirmation
    _wait_for_confirmation(client, txid)
    print(f"Voter {voter_address[:8]}... opted in successfully")
    
    return txid


def submit_vote(voter_mnemonic: str, app_id: int, candidate_id: int) -> Optional[str]:
    """
    Submit a vote for a candidate.
    
    Args:
        voter_mnemonic: Mnemonic of the voter account
        app_id: Application ID
        candidate_id: ID of the candidate to vote for
    
    Returns:
        Transaction ID if successful, None otherwise
    """
    client = _get_algod_client()
    if not client:
        print("Algod client not available")
        return None
    
    # Get voter credentials
    voter_private_key = algo_mnemonic.to_private_key(voter_mnemonic)
    voter_address = algo_mnemonic.to_public_key(voter_mnemonic)
    
    # Get suggested params
    params = client.suggested_params()
    
    # Application arguments: "vote" command and candidate_id
    app_args = [
        "vote".encode('utf-8'),
        candidate_id.to_bytes(8, 'big')
    ]
    
    # Create application call transaction
    txn = transaction.ApplicationNoOpTxn(
        sender=voter_address,
        sp=params,
        index=app_id,
        app_args=app_args
    )
    
    # Sign and send
    signed_txn = txn.sign(voter_private_key)
    txid = client.send_transaction(signed_txn)
    
    # Wait for confirmation
    _wait_for_confirmation(client, txid)
    print(f"Vote submitted successfully. TxID: {txid}")
    
    return txid


def get_voter_status(voter_address: str, app_id: int) -> Optional[Dict]:
    """
    Get voter's local state (if they've voted and for whom).
    
    Args:
        voter_address: Address of the voter
        app_id: Application ID
    
    Returns:
        Dict with 'voted' (bool) and 'candidate_id' (int or None)
    """
    client = _get_algod_client()
    if not client:
        return None
    
    try:
        account_info = client.account_info(voter_address)
        
        # Find the app's local state
        for app in account_info.get('apps-local-state', []):
            if app['id'] == app_id:
                state_dict = {}
                for kv in app.get('key-value', []):
                    key = base64.b64decode(kv['key']).decode('utf-8')
                    if kv['value']['type'] == 1:  # uint
                        state_dict[key] = kv['value']['uint']
                
                return {
                    'voted': state_dict.get('Voted', 0) == 1,
                    'candidate_id': state_dict.get('CandidateID')
                }
        
        return {'voted': False, 'candidate_id': None}
    except Exception as e:
        print(f"Error getting voter status: {e}")
        return None


def get_all_votes(app_id: int) -> Dict[int, int]:
    """
    Get vote counts by reading all accounts opted into the app.
    
    Note: This is a simplified version. In production, you'd use an indexer
    for better performance.
    
    Args:
        app_id: Application ID
    
    Returns:
        Dict mapping candidate_id -> vote_count
    """
    # This would require indexer or scanning all accounts
    # For now, return empty dict
    # Implementation would use algorand_reader.py logic
    return {}
