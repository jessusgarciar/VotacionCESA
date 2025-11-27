import os
import base64
from algosdk.v2client import algod
from algosdk import account, mnemonic
from algosdk import account, mnemonic, transaction

# Configure these based on your sandbox/node
ALGOD_ADDRESS = "http://localhost:4001"
ALGOD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result']), compile_response['hash']

def main():
    try:
        client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)
    except Exception as e:
        print(f"Could not connect to Algod: {e}")
        return

    print("Compiling approval.teal...")
    with open("approval.teal", "r") as f:
        approval_source = f.read()
    
    try:
        approval_bin, approval_hash = compile_program(client, approval_source)
        print(f"Approval Program Hash: {approval_hash}")
    except Exception as e:
        print(f"Error compiling approval.teal: {e}")

    print("Compiling clear.teal...")
    with open("clear.teal", "r") as f:
        clear_source = f.read()

    try:
        clear_bin, clear_hash = compile_program(client, clear_source)
        print(f"Clear Program Hash: {clear_hash}")
    except Exception as e:
        print(f"Error compiling clear.teal: {e}")

if __name__ == "__main__":
    main()
