Algorand Sandbox - quick start (for development)

This project uses Algorand for voting verification and supports testing locally with Algorand Sandbox.
Below are quick instructions to run a local sandbox and wire the Django project to it.

Requirements

- WSL2 on Windows (recommended) or a Linux/macOS shell
- Docker

Get the sandbox

1. Clone the official Algorand sandbox repo (in WSL or Linux/macOS):
2. Enter the sandbox folder:
   cd sandbox
3. Start the sandbox:
   ./sandbox up

Sandbox outputs

- After the sandbox starts, it prints configuration including algod/token and ports.
- Typical local Algod address: http://localhost:4001
- Typical token: printed in the sandbox output or available under sandbox folder files

Wire Django to the sandbox (example, from PowerShell or WSL environment where Django runs)

- Export env vars (PowerShell example):
  $env:ALGOD_ADDRESS='http://localhost:4001'
  $env:ALGOD_TOKEN='REPLACE_WITH_TOKEN_FROM_SANDBOX'
  $env:ALGORAND_APP_ID='1006'

- Start Django from the directory containing `manage.py`:
  python manage.py runserver

Testing address registration

- Use the provided `check_address.py` script (next to `manage.py`) to verify if an address is opted-in:
  python check_address.py --address <ALG_ADDRESS> --app <APP_ID>

Notes

- Sandbox is recommended for contract development and local E2E tests.
- For TestNet integration tests, use PureStake or another provider and set `PURESTAKE_APIKEY` + `ALGOD_ADDRESS` accordingly in env vars.
- When moving to production, replace sandbox values with real provider credentials or your managed node.
