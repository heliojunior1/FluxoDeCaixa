"""Debug script to verify DFC calculation values."""
from datetime import date
from src.fluxocaixa.models import db
from src.fluxocaixa.services.relatorio.dfc_service import get_dfc_data
from src.fluxocaixa import create_app

app = create_app()

with app.app_context():
    # Get DFC data for January 2025
    result = get_dfc_data(
        periodo='ano',
        ano_selecionado=2025,
        mes_selecionado=None,
        meses_selecionados=[1],  # January only
        estrategia='realizado',
        cenario_selecionado_id=None
    )
    
    print("=== DFC Data Debug ===")
    print(f"\nHeaders: {result['headers']}")
    print(f"\nTotal for January (index 0): R$ {result['totals'][0]:,.2f}")
    print(f"Resultado dia: R$ {result['resultado_dia'][0]:,.2f}")
    
    print("\n=== Breakdown by Root Qualificador ===")
    for root in result['dre_data']:
        jan_value = root['values'][0]
        print(f"\n{root['number']} - {root['name']}: R$ {jan_value:,.2f}")
        
        # Show children
        def print_children(node, indent=1):
            for child in node['children']:
                child_jan = child['values'][0]
                if abs(child_jan) > 0.01:  # Only show non-zero
                    print(f"{'  ' * indent}{child['number']} - {child['name']}: R$ {child_jan:,.2f}")
                print_children(child, indent + 1)
        
        print_children(root)
    
    print("\n=== Expected Calculation ===")
    print("Receita Líquida: R$ 1,882,178,940.00")
    print("Despesas: R$ 1,876,129,500.00")
    print("Expected Balance: R$ 6,049,440.00")
    print(f"\nActual Balance: R$ {result['resultado_dia'][0]:,.2f}")
    print(f"Difference: R$ {result['resultado_dia'][0] - 6049440.00:,.2f}")
