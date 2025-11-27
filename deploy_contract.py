"""
Script para desplegar el smart contract de votación.

Este script:
1. Compila y despliega el contrato en Algorand
2. Guarda el APP_ID en el archivo .env
3. Muestra las instrucciones para los votantes

Requisitos:
- Tener un nodo Algorand corriendo (o usar AlgoNode/PureStake API)
- Configurar ALGOD_ADDRESS y ALGOD_TOKEN en .env
- Tener la mnemonic del creador
"""
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VotacionCESA.settings')

import django
django.setup()

from votaciones.algorand_smart_contract import create_voting_app


def main():
    print("=" * 60)
    print("DESPLIEGUE DEL SMART CONTRACT DE VOTACIÓN")
    print("=" * 60)
    
    # Get creator mnemonic
    creator_mnemonic = os.environ.get('ALGORAND_CREATOR_MNEMONIC')
    if not creator_mnemonic:
        print("\nALGORAND_CREATOR_MNEMONIC no está configurada en .env")
        print("Esta es la cuenta que creará y controlará la aplicación.")
        creator_mnemonic = input("\nIngresa la mnemonic del creador (25 palabras): ").strip()
        
        if not creator_mnemonic:
            print("Mnemonic requerida")
            sys.exit(1)
    
    # Configure timestamps
    print("\nConfiguración de fechas")
    print("-" * 60)
    
    now = datetime.now()
    
    # Defaults: registration starts now, ends in 7 days
    # Voting starts in 7 days, ends in 14 days
    reg_begin = now
    reg_end = now + timedelta(days=7)
    vote_begin = reg_end
    vote_end = vote_begin + timedelta(days=7)
    
    print(f"Inicio de registro: {reg_begin.strftime('%Y-%m-%d %H:%M')}")
    print(f"Fin de registro:    {reg_end.strftime('%Y-%m-%d %H:%M')}")
    print(f"Inicio de votación: {vote_begin.strftime('%Y-%m-%d %H:%M')}")
    print(f"Fin de votación:    {vote_end.strftime('%Y-%m-%d %H:%M')}")
    
    confirm = input("\n¿Usar estas fechas? (s/n): ").lower()
    if confirm != 's':
        print("Puedes personalizar las fechas editando este script.")
        sys.exit(0)
    
    # Convert to Unix timestamps
    reg_begin_ts = int(reg_begin.timestamp())
    reg_end_ts = int(reg_end.timestamp())
    vote_begin_ts = int(vote_begin.timestamp())
    vote_end_ts = int(vote_end.timestamp())
    
    print("Desplegando smart contract...")
    print("-" * 60)
    
    try:
        app_id = create_voting_app(
            creator_mnemonic=creator_mnemonic,
            reg_begin=reg_begin_ts,
            reg_end=reg_end_ts,
            vote_begin=vote_begin_ts,
            vote_end=vote_end_ts,
            approval_teal_path="approval.teal",
            clear_teal_path="clear.teal"
        )
        
        if app_id:
            print(f"¡Smart contract desplegado exitosamente!")
            print(f"   APP_ID: {app_id}")
            
            # Update .env file
            env_path = ".env"
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
                
                # Check if ALGORAND_APP_ID exists
                found = False
                for i, line in enumerate(lines):
                    if line.startswith('ALGORAND_APP_ID='):
                        lines[i] = f'ALGORAND_APP_ID={app_id}\n'
                        found = True
                        break
                
                if not found:
                    lines.append(f'\nALGORAND_APP_ID={app_id}\n')
                
                with open(env_path, 'w') as f:
                    f.writelines(lines)
                
                print(f"\n ALGORAND_APP_ID guardado en .env")
            
            print("\n" + "=" * 60)
            print("PRÓXIMOS PASOS")
            print("=" * 60)
            print("\n1. Los votantes deben hacer OptIn a la aplicación:")
            print(f"   python manage.py voter_optin --app-id {app_id}")
            print("\n2. Durante el período de votación, pueden votar:")
            print(f"   python manage.py submit_vote --app-id {app_id} --candidate-id <ID>")
            print("\n3. Actualiza tus vistas para usar:")
            print("   from votaciones.algorand_smart_contract import submit_vote, voter_optin")
            
        else:
            print("\n Error al desplegar el smart contract")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
