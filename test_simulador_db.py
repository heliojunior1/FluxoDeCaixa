"""
Test script to verify database tables are created correctly.
Run this after starting the app with: python app.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fluxocaixa.models import db, SimuladorCenario, CenarioReceita, CenarioDespesa

def test_tables():
    print("Testing database tables for Simulador de Cenários...")
    
    # Test table creation
    try:
        # Query should work if tables exist
        simuladores = SimuladorCenario.query.all()
        print(f"✓ SimuladorCenario table exists. Count: {len(simuladores)}")
        
        receitas = CenarioReceita.query.all()
        print(f"✓ CenarioReceita table exists. Count: {len(receitas)}")
        
        despesas = CenarioDespesa.query.all()
        print(f"✓ CenarioDespesa table exists. Count: {len(despesas)}")
        
        print("\n✓ All tables created successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

if __name__ == '__main__':
    # Create tables
    db.create_all()
    print("Database tables created/verified.\n")
    
    # Test
    test_tables()
