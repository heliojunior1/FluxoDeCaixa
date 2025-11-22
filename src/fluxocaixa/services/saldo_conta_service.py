"""Service layer for SaldoConta (Bank Account Balance) operations."""
from datetime import date
from io import BytesIO, StringIO
import csv
import openpyxl

from ..domain import SaldoContaCreate, SaldoContaUpdate
from ..repositories import SaldoContaRepository, ContaBancariaRepository


def list_saldos_conta(
    seq_conta: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    repo: SaldoContaRepository | None = None
):
    """List bank account balances with optional filters.
    
    Args:
        seq_conta: Optional account filter
        data_inicio: Optional start date filter
        data_fim: Optional end date filter
        repo: Optional repository instance for dependency injection
        
    Returns:
        List of SaldoConta objects
    """
    repo = repo or SaldoContaRepository()
    return repo.list(seq_conta=seq_conta, data_inicio=data_inicio, data_fim=data_fim)


def get_saldo_conta(seq_saldo_conta: int, repo: SaldoContaRepository | None = None):
    """Get a single bank account balance by ID.
    
    Args:
        seq_saldo_conta: Balance record ID
        repo: Optional repository instance
        
    Returns:
        SaldoConta object or None if not found
    """
    repo = repo or SaldoContaRepository()
    from ..models import SaldoConta
    return repo.session.query(SaldoConta).get(seq_saldo_conta)


def create_saldo_conta(data: SaldoContaCreate, repo: SaldoContaRepository | None = None):
    """Create a new bank account balance record.
    
    Args:
        data: Validated creation data
        repo: Optional repository instance
        
    Returns:
        Created SaldoConta object
    """
    repo = repo or SaldoContaRepository()
    # Default user ID to 1 (system user)
    return repo.create(
        seq_conta=data.seq_conta,
        dat_saldo=data.dat_saldo,
        val_saldo=data.val_saldo,
        cod_pessoa_inclusao=1
    )


def update_saldo_conta(
    seq_saldo_conta: int,
    data: SaldoContaUpdate,
    repo: SaldoContaRepository | None = None
):
    """Update an existing bank account balance record.
    
    Args:
        seq_saldo_conta: Balance record ID
        data: Validated update data
        repo: Optional repository instance
        
    Returns:
        Updated SaldoConta object or None if not found
    """
    repo = repo or SaldoContaRepository()
    # Default user ID to 1 (system user)
    return repo.update(
        seq_saldo_conta=seq_saldo_conta,
        val_saldo=data.val_saldo,
        cod_pessoa_alteracao=1
    )


def delete_saldo_conta(seq_saldo_conta: int, repo: SaldoContaRepository | None = None):
    """Delete a bank account balance record.
    
    Args:
        seq_saldo_conta: Balance record ID
        repo: Optional repository instance
        
    Returns:
        True if deleted, False if not found
    """
    repo = repo or SaldoContaRepository()
    return repo.delete(seq_saldo_conta)


def import_saldos_service(content: bytes, filename: str) -> dict:
    """Import multiple bank account balance records from a CSV or XLSX file.
    
    Args:
        content: File content as bytes
        filename: Name of the uploaded file
        
    Returns:
        Dictionary with 'sucesso' count and 'erros' list
    """
    rows: list[dict] = []
    
    # Parse file based on extension
    if filename.lower().endswith('.csv'):
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(StringIO(text))
        for row in reader:
            rows.append({k.strip(): v for k, v in row.items()})
    elif filename.lower().endswith(('.xlsx', '.xls')):
        wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        headers = [str(c).strip() if c else '' for c in next(ws.iter_rows(values_only=True))]
        for row in ws.iter_rows(min_row=2, values_only=True):
            data = {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
            rows.append(data)
    else:
        return {"sucesso": 0, "erros": ["Formato de arquivo não suportado"]}
    
    # Initialize repositories
    saldo_repo = SaldoContaRepository()
    conta_repo = ContaBancariaRepository()
    
    # Pre-fetch accounts
    contas = conta_repo.list_active()
    contas_map = {}
    for conta in contas:
        key = f"{conta.cod_banco}-{conta.num_agencia}-{conta.num_conta}".lower()
        contas_map[key] = conta.seq_conta
    
    count = 0
    errors = []
    saldos_data = []
    
    try:
        for i, item in enumerate(rows, start=2):
            # Get fields with various naming conventions
            dat = item.get('Data') or item.get('data') or item.get('dat_saldo')
            banco = item.get('Banco') or item.get('banco') or item.get('cod_banco')
            agencia = item.get('Agência') or item.get('Agencia') or item.get('agencia') or item.get('num_agencia')
            conta = item.get('Conta') or item.get('conta') or item.get('num_conta')
            valor = item.get('Saldo') or item.get('saldo') or item.get('Valor') or item.get('valor') or item.get('val_saldo')
            
            # Validate required fields
            if not (dat and banco and agencia and conta and valor is not None):
                errors.append(f"Linha {i}: Dados incompletos (Data, Banco, Agência, Conta ou Saldo faltando)")
                continue
            
            # Parse date
            from datetime import datetime
            if isinstance(dat, datetime):
                dat = dat.date()
            elif isinstance(dat, str):
                try:
                    dat = date.fromisoformat(dat)
                except ValueError:
                    errors.append(f"Linha {i}: Data inválida '{dat}'")
                    continue
            
            # Find account
            key = f"{str(banco).strip()}-{str(agencia).strip()}-{str(conta).strip()}".lower()
            seq_conta = contas_map.get(key)
            if not seq_conta:
                errors.append(f"Linha {i}: Conta não encontrada '{banco}-{agencia}-{conta}'")
                continue
            
            # Parse value
            try:
                val_saldo = float(valor)
            except (ValueError, TypeError):
                errors.append(f"Linha {i}: Valor inválido '{valor}'")
                continue
            
            # Add to batch
            saldos_data.append({
                'seq_conta': seq_conta,
                'dat_saldo': dat,
                'val_saldo': val_saldo,
                'cod_pessoa_inclusao': 1,
                'dat_inclusao': date.today()
            })
            count += 1
        
        # Bulk insert
        if saldos_data:
            saldo_repo.bulk_create(saldos_data)
        
        return {"sucesso": count, "erros": errors}
    except Exception as e:
        errors.append(f"Erro fatal durante importação: {str(e)}")
        return {"sucesso": 0, "erros": errors}
