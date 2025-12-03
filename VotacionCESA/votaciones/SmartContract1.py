#!/usr/bin/env python3
"""
Script de Gestión del Smart Contract de Votación - Sistema CESA

Este script proporciona utilidades para interactuar con el contrato inteligente
de votación desplegado en Algorand TestNet/MainNet.

Funcionalidades:
1. Desplegar nuevo contrato de votación
2. Verificar estado del contrato
3. Registrar votantes (OptIn)
4. Simular votación
5. Consultar resultados

Uso:
    python SmartContract1.py deploy                    # Desplegar contrato
    python SmartContract1.py status <APP_ID>           # Ver estado del contrato
    python SmartContract1.py optin <APP_ID> <MNEMONIC> # Registrar votante
    python SmartContract1.py vote <APP_ID> <MNEMONIC>  # Simular voto
    python SmartContract1.py info <APP_ID>             # Info detallada

Requisitos:
- py-algorand-sdk instalado
- Variables de entorno configuradas o archivo .env
"""

import base64
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    from algosdk import account, mnemonic, transaction
    from algosdk.v2client import algod
    from algosdk.encoding import decode_address, encode_address
    ALGOSDK_AVAILABLE = True
except ImportError:
    print("Error: py-algorand-sdk no está instalado")
    print("Instalar con: pip install py-algorand-sdk")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

ALGOD_ADDRESS = os.environ.get('ALGOD_ADDRESS', 'http://localhost:4001')
ALGOD_TOKEN = os.environ.get('ALGOD_TOKEN', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
ALGOD_HEADERS = {}

# Rutas de archivos TEAL
APPROVAL_TEAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'approval.teal')
CLEAR_TEAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'clear.teal')

# Cuentas predefinidas de Algorand Sandbox (con fondos)
# Estas son las cuentas estándar que vienen configuradas en el Sandbox oficial
SANDBOX_ACCOUNTS = [
    {
        'name': 'Account 1 (Primary)',
        'mnemonic': 'advice pudding treat near rule blouse same whisper inner electric quit surface sunny dismiss leader blood seat clown cost exist hospital century reform able sponsor'
    },
    {
        'name': 'Account 2',
        'mnemonic': 'call boy rubber fashion arch day capable one sweet skate outside purse six early learn tuition eagle love breeze pizza loud today popular able divide'
    },
    {
        'name': 'Account 3',
        'mnemonic': 'auction inquiry lava second expand liberty glass involve ginger illness length room item discover ahead table doctor term tackle cement bonus profit right above catch'
    }
]


# ============================================================================
# UTILIDADES
# ============================================================================

def normalize_mnemonic(raw: str) -> str:
    """Normaliza una mnemonic eliminando espacios extras."""
    return " ".join(raw.strip().split())


def load_account(mnemonic_raw: str):
    """Carga una cuenta desde mnemonic y devuelve (private_key, address)."""
    mn = normalize_mnemonic(mnemonic_raw)
    words = mn.split()
    if len(words) != 25:
        raise ValueError(f"Mnemonic tiene {len(words)} palabras (debe ser 25).")
    sk = mnemonic.to_private_key(mn)
    addr = account.address_from_private_key(sk)
    return sk, addr


def generate_account():
    """Genera una nueva cuenta de Algorand y devuelve (private_key, address, mnemonic)."""
    private_key, address = account.generate_account()
    mn = mnemonic.from_private_key(private_key)
    return private_key, address, mn


def is_sandbox():
    """Detecta si estamos usando Algorand Sandbox."""
    algod_addr = ALGOD_ADDRESS.lower()
    return 'localhost' in algod_addr or '127.0.0.1' in algod_addr or 'sandbox' in algod_addr


def get_sandbox_account(index: int = 0):
    """Obtiene una cuenta predefinida del Sandbox."""
    if index >= len(SANDBOX_ACCOUNTS):
        raise ValueError(f"Índice {index} fuera de rango. Sandbox tiene {len(SANDBOX_ACCOUNTS)} cuentas.")
    
    account_info = SANDBOX_ACCOUNTS[index]
    sk, addr = load_account(account_info['mnemonic'])
    return sk, addr, account_info['name']


def compile_teal(filepath: str, client: algod.AlgodClient) -> bytes:
    """Compila un archivo TEAL y devuelve el bytecode."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No existe archivo TEAL: {filepath}")
    
    print(f"[*] Compilando: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()
    
    resp = client.compile(src)
    return base64.b64decode(resp["result"])


def wait_for_confirmation(client: algod.AlgodClient, txid: str, timeout: int = 4):
    """Espera confirmación de transacción."""
    start_round = client.status()["last-round"] + 1
    current_round = start_round

    while current_round < start_round + timeout:
        try:
            pending_txn = client.pending_transaction_info(txid)
        except Exception:
            return None
        
        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn
        elif pending_txn.get("pool-error"):
            raise Exception(f'Pool error: {pending_txn["pool-error"]}')
        
        client.status_after_block(current_round)
        current_round += 1
    
    raise Exception(f"Transacción no confirmada después de {timeout} rondas")


def decode_state(state_array) -> Dict[str, Any]:
    """Decodifica el estado global/local de una aplicación."""
    decoded = {}
    for kv in state_array:
        key = base64.b64decode(kv["key"]).decode('utf-8')
        value_obj = kv["value"]
        
        if value_obj["type"] == 1:  # bytes
            try:
                decoded[key] = base64.b64decode(value_obj["bytes"])
            except:
                decoded[key] = value_obj["bytes"]
        elif value_obj["type"] == 2:  # uint
            decoded[key] = value_obj["uint"]
        else:
            decoded[key] = value_obj
    
    return decoded


def format_timestamp(ts: int) -> str:
    """Formatea un timestamp Unix a string legible."""
    if ts == 0:
        return "No configurado"
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def deploy_contract(creator_mnemonic: Optional[str] = None, 
                   reg_begin: Optional[int] = None,
                   reg_end: Optional[int] = None,
                   vote_begin: Optional[int] = None,
                   vote_end: Optional[int] = None,
                   use_sandbox_account: int = -1) -> int:
    """
    Despliega el smart contract de votación en Algorand.
    
    Args:
        creator_mnemonic: Mnemonic de la cuenta creadora (opcional si usa sandbox)
        reg_begin: Timestamp inicio de registro (default: ahora)
        reg_end: Timestamp fin de registro (default: +7 días)
        vote_begin: Timestamp inicio de votación (default: +7 días)
        vote_end: Timestamp fin de votación (default: +30 días)
        use_sandbox_account: Índice de cuenta sandbox a usar (-1 = no usar)
    
    Returns:
        app_id: ID de la aplicación creada
    """
    print("\n" + "=" * 70)
    print("DESPLIEGUE DEL SMART CONTRACT DE VOTACIÓN - SISTEMA CESA")
    print("=" * 70)
    
    # Conectar a Algorand
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    # Determinar si usar Sandbox
    using_sandbox = is_sandbox()
    if using_sandbox:
        print(f"\n[*] Detectado Algorand Sandbox: {ALGOD_ADDRESS}")
    
    # Cargar cuenta creadora
    if use_sandbox_account >= 0:
        creator_sk, creator_addr, account_name = get_sandbox_account(use_sandbox_account)
        print(f"\n[+] Usando cuenta Sandbox: {account_name}")
        print(f"[+] Dirección: {creator_addr}")
    elif creator_mnemonic:
        creator_sk, creator_addr = load_account(creator_mnemonic)
        print(f"\n[+] Cuenta creadora: {creator_addr}")
    else:
        raise ValueError("Debes proporcionar creator_mnemonic o use_sandbox_account")
    
    # Verificar balance
    account_info = client.account_info(creator_addr)
    balance = account_info.get('amount', 0) / 1_000_000  # microAlgos a Algos
    print(f"[+] Balance: {balance:.6f} ALGO")
    
    if balance < 0.1:
        print("\n[!] ADVERTENCIA: Balance bajo. Necesitas al menos 0.1 ALGO para crear la aplicación.")
        print(f"[!] Puedes obtener ALGO de prueba en: https://testnet.algoexplorer.io/dispenser")
    
    # Configurar timestamps por defecto
    now = int(time.time())
    reg_begin = reg_begin or now
    reg_end = reg_end or (now + 7 * 24 * 3600)  # +7 días
    vote_begin = vote_begin or reg_end
    vote_end = vote_end or (now + 30 * 24 * 3600)  # +30 días
    
    print(f"\n[*] Configuración de fechas:")
    print(f"    Registro: {format_timestamp(reg_begin)} → {format_timestamp(reg_end)}")
    print(f"    Votación: {format_timestamp(vote_begin)} → {format_timestamp(vote_end)}")
    
    # Compilar contratos
    print(f"\n[*] Compilando contratos TEAL...")
    approval_prog = compile_teal(APPROVAL_TEAL_PATH, client)
    clear_prog = compile_teal(CLEAR_TEAL_PATH, client)
    print(f"[+] Approval program: {len(approval_prog)} bytes")
    print(f"[+] Clear program: {len(clear_prog)} bytes")
    
    # Configurar esquemas de estado
    global_schema = transaction.StateSchema(num_uints=4, num_byte_slices=1)
    local_schema = transaction.StateSchema(num_uints=1, num_byte_slices=0)
    
    # Preparar argumentos (timestamps como bytes de 8 bytes en big-endian)
    app_args = [
        reg_begin.to_bytes(8, 'big'),
        reg_end.to_bytes(8, 'big'),
        vote_begin.to_bytes(8, 'big'),
        vote_end.to_bytes(8, 'big'),
    ]
    
    # Crear transacción de creación
    params = client.suggested_params()
    
    create_txn = transaction.ApplicationCreateTxn(
        sender=creator_addr,
        sp=params,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_prog,
        clear_program=clear_prog,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=app_args,
    )
    
    # Firmar y enviar
    print(f"\n[*] Creando aplicación en blockchain...")
    signed_txn = create_txn.sign(creator_sk)
    txid = client.send_transaction(signed_txn)
    print(f"[+] Transaction ID: {txid}")
    
    # Esperar confirmación
    print(f"[*] Esperando confirmación...")
    confirmed_txn = wait_for_confirmation(client, txid)
    app_id = confirmed_txn["application-index"]
    
    print(f"\n{'=' * 70}")
    print(f"✓ CONTRATO DESPLEGADO EXITOSAMENTE")
    print(f"{'=' * 70}")
    print(f"\nAPP ID: {app_id}")
    print(f"Creator: {creator_addr}")
    print(f"Transaction: {txid}")
    # Mostrar enlace apropiado según el entorno
    if using_sandbox:
        print(f"\n[*] Aplicación desplegada en Sandbox local")
        print(f"    Puedes consultar el estado con: python SmartContract1.py status {app_id}")
    else:
        print(f"\nExplorador TestNet:")
        print(f"https://testnet.algoexplorer.io/application/{app_id}")
    
    print(f"\n[!] IMPORTANTE: Guarda este APP_ID en tu archivo .env:")
    print(f"    ALGORAND_APP_ID={app_id}")
    
    return app_id


def get_contract_status(app_id: int):
    """Muestra el estado actual del contrato."""
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    print(f"\n" + "=" * 70)
    print(f"ESTADO DEL CONTRATO - APP ID: {app_id}")
    print("=" * 70)
    
    try:
        app_info = client.application_info(app_id)
    except Exception as e:
        print(f"\n[!] Error: No se pudo obtener información de la aplicación {app_id}")
        print(f"    {str(e)}")
        return
    
    params = app_info.get("params", {})
    creator = params.get("creator", "N/A")
    
    print(f"\n[+] Creador: {creator}")
    print(f"[+] Fecha de creación: {app_info.get('created-at-round', 'N/A')}")
    
    # Estado global
    global_state = params.get("global-state", [])
    if global_state:
        state = decode_state(global_state)
        
        print(f"\n[*] Estado Global:")
        print(f"    {'─' * 60}")
        
        creator_bytes = state.get("Creator")
        if creator_bytes:
            creator_addr = encode_address(creator_bytes) if len(creator_bytes) == 32 else "N/A"
            print(f"    Creator Address : {creator_addr}")
        
        reg_begin = state.get("RegBegin", 0)
        reg_end = state.get("RegEnd", 0)
        vote_begin = state.get("VoteBegin", 0)
        vote_end = state.get("VoteEnd", 0)
        
        print(f"\n    Período de Registro:")
        print(f"      Inicio : {format_timestamp(reg_begin)}")
        print(f"      Fin    : {format_timestamp(reg_end)}")
        
        print(f"\n    Período de Votación:")
        print(f"      Inicio : {format_timestamp(vote_begin)}")
        print(f"      Fin    : {format_timestamp(vote_end)}")
        
        # Estado actual
        now = int(time.time())
        if now < reg_begin:
            status = "Pendiente (no iniciado)"
        elif reg_begin <= now < reg_end:
            status = "Registro abierto"
        elif reg_end <= now < vote_begin:
            status = "Entre registro y votación"
        elif vote_begin <= now < vote_end:
            status = "Votación activa"
        else:
            status = "Finalizado"
        
        print(f"\n    Estado actual: {status}")
    
    print(f"\nEsquemas de estado:")
    print(f"    Global: {params.get('global-state-schema', {})}")
    print(f"    Local : {params.get('local-state-schema', {})}")
    
    print(f"\n" + "=" * 70)


def voter_optin(app_id: int, voter_mnemonic: str):
    """Registra un votante en el contrato (OptIn)."""
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    voter_sk, voter_addr = load_account(voter_mnemonic)
    
    print(f"\nRegistrando votante: {voter_addr}")
    print(f"En aplicación: {app_id}")
    
    params = client.suggested_params()
    
    optin_txn = transaction.ApplicationOptInTxn(
        sender=voter_addr,
        sp=params,
        index=app_id
    )
    
    signed_txn = optin_txn.sign(voter_sk)
    txid = client.send_transaction(signed_txn)
    
    print(f"[+] Transaction enviada: {txid}")
    print(f"Esperando confirmación...")
    
    wait_for_confirmation(client, txid)
    
    print(f"Votante registrado exitosamente")
    print(f"El votante puede ahora emitir su voto durante el período de votación")


def simulate_vote(app_id: int, voter_mnemonic: str):
    """Simula un voto (NoOp call)."""
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    voter_sk, voter_addr = load_account(voter_mnemonic)
    
    print(f"\n[*] Simulando voto de: {voter_addr}")
    print(f"[*] En aplicación: {app_id}")
    
    params = client.suggested_params()
    
    # Llamada NoOp (voto)
    vote_txn = transaction.ApplicationNoOpTxn(
        sender=voter_addr,
        sp=params,
        index=app_id,
        app_args=[]  # El contrato solo marca como votado
    )
    
    signed_txn = vote_txn.sign(voter_sk)
    txid = client.send_transaction(signed_txn)
    
    print(f"[+] Transaction enviada: {txid}")
    print(f"[*] Esperando confirmación...")
    
    wait_for_confirmation(client, txid)
    
    print(f"[✓] Voto registrado exitosamente en blockchain")


# ============================================================================
# INTERFAZ DE LÍNEA DE COMANDOS
# ============================================================================

def list_sandbox_accounts():
    """Lista las cuentas predefinidas de Sandbox."""
    print("\n" + "=" * 70)
    print("CUENTAS PREDEFINIDAS DE ALGORAND SANDBOX")
    print("=" * 70)
    
    for i, acc in enumerate(SANDBOX_ACCOUNTS):
        print(f"\n[{i}] {acc['name']}")
        sk, addr = load_account(acc['mnemonic'])
        print(f"    Dirección: {addr}")
        print(f"    Mnemonic: {acc['mnemonic'][:50]}...")
    
    print("\n" + "=" * 70)


def generate_new_account():
    """Genera y muestra una nueva cuenta de Algorand."""
    print("\n" + "=" * 70)
    print("GENERANDO NUEVA CUENTA DE ALGORAND")
    print("=" * 70)
    
    private_key, address, mn = generate_account()
    
    print(f"\n[+] Nueva cuenta generada:")
    print(f"    Dirección: {address}")
    print(f"\n[+] Mnemonic (guárdala en lugar seguro):")
    print(f"    {mn}")
    
    print(f"\n[!] IMPORTANTE:")
    print(f"    - Esta cuenta NO tiene fondos")
    print(f"    - Para TestNet, obtén ALGO en: https://testnet.algoexplorer.io/dispenser")
    print(f"    - Para Sandbox, las cuentas predefinidas ya tienen fondos")
    
    print("\n" + "=" * 70)


def get_sandbox_funded_accounts():
    """Obtiene cuentas del Sandbox que tengan fondos suficientes."""
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    funded_accounts = []
    
    for i, acc in enumerate(SANDBOX_ACCOUNTS):
        try:
            sk, addr = load_account(acc['mnemonic'])
            account_info = client.account_info(addr)
            balance = account_info.get('amount', 0) / 1_000_000
            
            if balance > 0.1:
                funded_accounts.append({
                    'index': i,
                    'name': acc['name'],
                    'address': addr,
                    'private_key': sk,
                    'balance': balance
                })
        except Exception:
            continue
    
    return funded_accounts


def check_sandbox_status():
    """Verifica el estado del Sandbox y proporciona ayuda."""
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO DEL SANDBOX")
    print("=" * 70)
    
    client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS, ALGOD_HEADERS)
    
    try:
        status = client.status()
        print(f"\n[✓] Sandbox conectado exitosamente")
        print(f"    Última ronda: {status.get('last-round', 'N/A')}")
        
        print(f"\n[*] Verificando balances de cuentas predefinidas:")
        for i, acc in enumerate(SANDBOX_ACCOUNTS):
            sk, addr = load_account(acc['mnemonic'])
            try:
                account_info = client.account_info(addr)
                balance = account_info.get('amount', 0) / 1_000_000
                status_icon = "✓" if balance > 0.1 else "✗"
                print(f"    [{status_icon}] Cuenta {i}: {balance:.6f} ALGO - {addr[:10]}...")
            except Exception as e:
                print(f"    [✗] Cuenta {i}: Error - {str(e)[:50]}")
        
        print(f"\n[*] Buscando cuentas con fondos en el Sandbox...")
        print(f"    Ejecuta en WSL: ./sandbox goal account list")
        print(f"\n[!] Para fondear manualmente una cuenta desde WSL:")
        print(f"    cd ~/sandbox")
        print(f"    ./sandbox goal clerk send -a 10000000 -f <CUENTA_ORIGEN> -t <TU_CUENTA>")
        print(f"\n[!] O resetea el Sandbox completamente:")
        print(f"    cd ~/sandbox")
        print(f"    ./sandbox down")
        print(f"    ./sandbox clean")
        print(f"    ./sandbox up")
        
    except Exception as e:
        print(f"\n[✗] No se pudo conectar al Sandbox")
        print(f"    Error: {str(e)}")
        print(f"\n[!] Verifica que el Sandbox esté corriendo:")
        print(f"    cd ~/sandbox")
        print(f"    ./sandbox up")
        print(f"\n[!] Verifica tu configuración .env:")
        print(f"    ALGOD_ADDRESS={ALGOD_ADDRESS}")
        print(f"    ALGOD_TOKEN={ALGOD_TOKEN[:20]}...")
    
    print("\n" + "=" * 70)


def print_usage():
    """Imprime instrucciones de uso."""
    print("""
Uso: python SmartContract1.py <comando> [argumentos]

Comandos disponibles:

  deploy                          Despliega nuevo contrato (detecta Sandbox automáticamente)
  deploy-sandbox [ACCOUNT_INDEX]  Despliega usando cuenta Sandbox (default: 0)
  deploy-mnemonic "MNEMONIC"      Despliega usando una mnemonic específica
  status <APP_ID>                 Muestra el estado del contrato
  optin <APP_ID> <MNEMONIC>       Registra un votante (OptIn)
  vote <APP_ID> <MNEMONIC>        Simula un voto
  accounts                        Lista cuentas predefinidas de Sandbox
  generate                        Genera una nueva cuenta
  check                           Diagnóstico del Sandbox (verifica conexión y balances)
  help                            Muestra esta ayuda

Ejemplos:

  # Desplegar en Sandbox (usa cuenta 0 automáticamente si detecta Sandbox)
  python SmartContract1.py deploy
  
  # Desplegar en Sandbox con cuenta específica
  python SmartContract1.py deploy-sandbox 1
  
  # Ver cuentas de Sandbox
  python SmartContract1.py accounts
  
  # Generar nueva cuenta
  python SmartContract1.py generate
  
  # Consultar estado
  python SmartContract1.py status 123456789
  
  # Registrar votante con mnemonic
  python SmartContract1.py optin 123456789 "word1 word2 ... word25"
  
  # Simular voto
  python SmartContract1.py vote 123456789 "word1 word2 ... word25"

Variables de entorno (archivo .env):
  ALGOD_ADDRESS       URL del nodo Algorand
                      - Sandbox: http://localhost:4001
                      - TestNet: https://testnet-api.algonode.cloud
  ALGOD_TOKEN         Token de autenticación
                      - Sandbox: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
                      - AlgoNode: (vacío)
  ALGORAND_CREATOR_MNEMONIC  Mnemonic para despliegues (opcional con Sandbox)
    """)


def main():
    """Función principal del script."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "deploy":
            # Auto-detectar Sandbox
            if is_sandbox():
                print("[*] Sandbox detectado. Usando cuenta predefinida 0...")
                deploy_contract(use_sandbox_account=0)
            else:
                creator_mnemonic = os.environ.get('ALGORAND_CREATOR_MNEMONIC')
                if not creator_mnemonic:
                    print("\n[!] ALGORAND_CREATOR_MNEMONIC no está configurada en .env")
                    creator_mnemonic = input("\nIngresa la mnemonic del creador (25 palabras): ").strip()
                
                deploy_contract(creator_mnemonic)
        
        elif command == "deploy-sandbox":
            account_index = 0
            if len(sys.argv) >= 3:
                account_index = int(sys.argv[2])
            
            deploy_contract(use_sandbox_account=account_index)
        
        elif command == "deploy-mnemonic":
            if len(sys.argv) < 3:
                print("[!] Error: Falta la mnemonic")
                print("Uso: python SmartContract1.py deploy-mnemonic \"word1 word2 ... word25\"")
                sys.exit(1)
            
            mnemonic_str = sys.argv[2]
            deploy_contract(creator_mnemonic=mnemonic_str)
        
        elif command == "accounts":
            list_sandbox_accounts()
        
        elif command == "generate":
            generate_new_account()
        
        elif command == "check":
            check_sandbox_status()
        
        elif command == "status":
            if len(sys.argv) < 3:
                print("[!] Error: Falta APP_ID")
                print("Uso: python SmartContract1.py status <APP_ID>")
                sys.exit(1)
            
            app_id = int(sys.argv[2])
            get_contract_status(app_id)
        
        elif command == "optin":
            if len(sys.argv) < 4:
                print("[!] Error: Faltan argumentos")
                print("Uso: python SmartContract1.py optin <APP_ID> <MNEMONIC>")
                sys.exit(1)
            
            app_id = int(sys.argv[2])
            mnemonic_str = sys.argv[3]
            voter_optin(app_id, mnemonic_str)
        
        elif command == "vote":
            if len(sys.argv) < 4:
                print("[!] Error: Faltan argumentos")
                print("Uso: python SmartContract1.py vote <APP_ID> <MNEMONIC>")
                sys.exit(1)
            
            app_id = int(sys.argv[2])
            mnemonic_str = sys.argv[3]
            simulate_vote(app_id, mnemonic_str)
        
        elif command in ["help", "-h", "--help"]:
            print_usage()
        
        else:
            print(f"[!] Comando desconocido: {command}")
            print_usage()
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n[!] Operación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
