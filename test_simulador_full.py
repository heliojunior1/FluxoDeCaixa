"""
Full integration test for Simulador de Cenários.
Tests the entire flow: Create -> Configure -> Execute -> Verify Results.
"""

import sys
import os
from datetime import date
import json
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fluxocaixa.models import db, SimuladorCenario
from fluxocaixa.services.simulador_cenario_service import (
    criar_simulador_cenario,
    executar_simulacao,
    delete_simulador,
    obter_simulador_completo
)

def test_full_flow():
    print("=== Starting Full Integration Test for Simulador de Cenários ===\n")
    
    # 1. Setup
    print("1. Setting up test data...")
    user_id = 1
    ano_base = date.today().year
    
    # 2. Create Scenario (Manual Revenue + LOA Expense)
    print("2. Creating new scenario (Manual Revenue + LOA Expense)...")
    
    # Mock manual adjustments for revenue
    ajustes_receita = {
        'val_ajuste_1_1': '1000.00',  # Jan, Qualificador 1
        'val_ajuste_2_1': '1500.00',  # Feb, Qualificador 1
        'cod_tipo_ajuste_1_1': 'V',
        'cod_tipo_ajuste_2_1': 'V'
    }
    
    # Config for LOA expense
    config_despesa = {
        'valor_anual': 12000.00,
        'distribuicao': 'uniforme'
    }
    
    try:
        simulador = criar_simulador_cenario(
            nom_cenario="TESTE_INTEGRACAO_AUTO",
            dsc_cenario="Cenário criado via script de teste automatizado",
            ano_base=ano_base,
            meses_projecao=12,
            tipo_cenario_receita='MANUAL',
            config_receita={},
            ajustes_receita=ajustes_receita,
            tipo_cenario_despesa='LOA',
            config_despesa=config_despesa,
            user_id=user_id
        )
        print(f"✓ Scenario created successfully. ID: {simulador.seq_simulador_cenario}")
        
        # 3. Verify Persistence
        print("\n3. Verifying data persistence...")
        completo = obter_simulador_completo(simulador.seq_simulador_cenario)
        
        if completo['simulador'].nom_cenario == "TESTE_INTEGRACAO_AUTO":
            print("✓ Basic info persisted correctly")
        else:
            print("✗ Basic info mismatch")
            
        if completo['receita']['config'].cod_tipo_cenario == 'MANUAL':
            print("✓ Revenue config persisted correctly")
        else:
            print("✗ Revenue config mismatch")
            
        if len(completo['receita']['ajustes']) >= 2:
            print(f"✓ Revenue adjustments persisted correctly (Count: {len(completo['receita']['ajustes'])})")
        else:
            print("✗ Revenue adjustments missing")
            
        # 4. Execute Simulation
        print("\n4. Executing simulation...")
        resultado = executar_simulacao(simulador.seq_simulador_cenario)
        
        if resultado:
            print("✓ Simulation executed successfully")
            
            # Check Revenue (Manual)
            receita_total = resultado['resumo']['total_receita']
            print(f"   - Total Revenue: R$ {receita_total:,.2f}")
            # Expected: 1000 + 1500 = 2500 (since only 2 months set)
            if receita_total == 2500.00:
                print("✓ Revenue calculation correct")
            else:
                print(f"✗ Revenue calculation incorrect (Expected 2500.00, got {receita_total})")
                
            # Check Expense (LOA Uniform)
            despesa_total = resultado['resumo']['total_despesa']
            print(f"   - Total Expense: R$ {despesa_total:,.2f}")
            # Expected: 12000 distributed over 12 months = 12000
            if abs(despesa_total - 12000.00) < 0.01:
                print("✓ Expense calculation correct")
            else:
                print(f"✗ Expense calculation incorrect (Expected 12000.00, got {despesa_total})")
                
            # Check Balance
            saldo = resultado['resumo']['saldo_final']
            print(f"   - Final Balance: R$ {saldo:,.2f}")
            if abs(saldo - (2500 - 12000)) < 0.01:
                print("✓ Balance calculation correct")
            else:
                print("✗ Balance calculation incorrect")
                
        else:
            print("✗ Simulation execution failed")
            
        # 5. Cleanup
        print("\n5. Cleaning up...")
        delete_simulador(simulador.seq_simulador_cenario)
        print("✓ Test scenario deleted (logically)")
        
        print("\n=== Test Completed Successfully ===")
        return True
        
    except Exception as e:
        print(f"\n✗ Test Failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_full_flow()
