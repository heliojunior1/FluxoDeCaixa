import sys
import os
from datetime import date
import pandas as pd

# Add src to PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fluxocaixa.models import db, SimuladorCenario, CenarioReceita, CenarioReceitaAjuste, Lancamento, Qualificador, TipoLancamento, OrigemLancamento, Orgao, ContaBancaria
from fluxocaixa.services.simulador_cenario_service import _executar_cenario_manual_receita

def verify():
    session = db.session()
    
    try:
        print("Setting up test data...")
        
        # 1. Setup dependencies if missing
        tipo = session.query(TipoLancamento).first()
        if not tipo:
            tipo = TipoLancamento(dsc_tipo_lancamento="Receita")
            session.add(tipo)
            session.commit()
            
        origem = session.query(OrigemLancamento).first()
        if not origem:
            origem = OrigemLancamento(dsc_origem="Manual")
            session.add(origem)
            session.commit()
            
        orgao = session.query(Orgao).first()
        if not orgao:
            orgao = Orgao(nom_orgao="Test Org")
            session.add(orgao)
            session.commit()
            
        conta = session.query(ContaBancaria).first()
        if not conta:
            conta = ContaBancaria(
                cod_banco="001",
                num_agencia="1234", 
                num_conta="56789",
                dsc_conta="Test Account"
            )
            session.add(conta)
            session.commit()

        # 2. Find a qualifier to use
        qual = session.query(Qualificador).first()
        if not qual:
            qual = Qualificador(dsc_qualificador="Test Qual", cod_tipo_lancamento=tipo.cod_tipo_lancamento)
            session.add(qual)
            session.commit()

        seq_qual = qual.seq_qualificador
        print(f"Using qualifier: {qual.dsc_qualificador} (ID: {seq_qual})")
        
        # 3. Insert realized data for 2023 (Base Year - 1)
        ano_base = 2024
        ano_ref = 2023
        
        # Clean up existing data for this qual/year to avoid noise
        session.query(Lancamento).filter(
            Lancamento.seq_qualificador == seq_qual,
            Lancamento.dat_lancamento >= date(ano_ref, 1, 1),
            Lancamento.dat_lancamento <= date(ano_ref, 12, 31)
        ).delete()
        
        # Insert 100.00 for Jan/2023
        lanc = Lancamento(
            seq_qualificador=seq_qual,
            dat_lancamento=date(ano_ref, 1, 15),
            val_lancamento=100.00,
            cod_tipo_lancamento=tipo.cod_tipo_lancamento,
            cod_origem_lancamento=origem.cod_origem_lancamento,
            seq_conta=conta.seq_conta,
            cod_pessoa_inclusao=1
        )
        session.add(lanc)
        session.commit()
        print(f"Inserted test data: 100.00 for Jan/{ano_ref}")
        
        # 4. Create adjustments
        # +2% for Jan
        ajuste = CenarioReceitaAjuste(
            seq_cenario_receita=999, # Dummy
            seq_qualificador=seq_qual,
            ano=ano_base,
            mes=1,
            cod_tipo_ajuste='P',
            val_ajuste=2.0
        )
        
        # 5. Run calculation
        print("Running calculation...")
        df = _executar_cenario_manual_receita([ajuste], ano_base, 12)
        
        # 6. Verify
        # Note: df['data'] contains Timestamp objects
        target_date = pd.Timestamp(f'{ano_base}-01-01')
        row = df[(df['seq_qualificador'] == seq_qual) & (df['data'] == target_date)]
        
        if not row.empty:
            val_proj = row.iloc[0]['valor_projetado']
            print(f"Projected Value for Jan/{ano_base}: {val_proj}")
            
            expected = 100.00 * 1.02
            if abs(val_proj - expected) < 0.01:
                print("SUCCESS: Calculation is correct! (100 * 1.02 = 102)")
            else:
                print(f"FAILURE: Expected {expected}, got {val_proj}")
        else:
            print(f"FAILURE: No projection found for Jan/{ano_base}.")
            print("DataFrame content:")
            print(df)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    verify()
