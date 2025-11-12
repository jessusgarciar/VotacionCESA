"""Small helper to check whether an Algorand address is opted-in (has local state)
for a given application id. Intended for development and quick verification.

Usage (from the directory that contains manage.py):

# set environment variables (example for PureStake TestNet):
# PowerShell example:
# $env:ALGOD_ADDRESS='https://testnet-algorand.api.purestake.io/ps2'
# $env:PURESTAKE_APIKEY='your_purestake_key'
# $env:ALGORAND_APP_ID='12345678'
# then run:
# python check_address.py --address YOUR_ADDRESS

The script reads ALGOD_ADDRESS, ALGOD_TOKEN, PURESTAKE_APIKEY, ALGORAND_APP_ID from env if not passed as args.
"""
import os
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', '-a', help='Algorand address to check')
    parser.add_argument('--app', '-p', help='Application ID (overrides ALGORAND_APP_ID env var)')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    address = args.address or os.getenv('TEST_ADDRESS')
    app_id = args.app or os.getenv('ALGORAND_APP_ID')
    algod_address = os.getenv('ALGOD_ADDRESS', 'http://localhost:4001')
    algod_token = os.getenv('ALGOD_TOKEN', '')
    pure_api = os.getenv('PURESTAKE_APIKEY')
    algod_headers = {'X-API-Key': pure_api} if pure_api else None

    if not address:
        print('Error: no address provided (use --address or set TEST_ADDRESS env var)')
        return
    if not app_id:
        print('Error: no app id provided (set ALGORAND_APP_ID env or pass --app)')
        return

    try:
        app_id = int(app_id)
    except Exception:
        print('Error: ALGORAND_APP_ID must be an integer')
        return

    try:
        from algosdk.v2client import algod
    except Exception as e:
        print('algosdk not installed. Install with: pip install py-algorand-sdk')
        print('Error:', e)
        return

    try:
        client = algod.AlgodClient(algod_token or '', algod_address, headers=algod_headers)
    except Exception as e:
        print('Could not create Algod client:', e)
        return

    try:
        info = client.account_info(address)
    except Exception as e:
        print('Error fetching account info:', e)
        return

    apps_local = info.get('apps-local-state', []) or []
    found = any(entry.get('id') == app_id for entry in apps_local)
    if found:
        print(f'Address {address} IS registered/opted-in for app {app_id}')
    else:
        print(f'Address {address} is NOT registered/opted-in for app {app_id}')


if __name__ == '__main__':
    main()
