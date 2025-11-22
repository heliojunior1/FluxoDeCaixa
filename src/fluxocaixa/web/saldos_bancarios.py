"""Web controller for bank balance (Saldos Bancários) management."""
from datetime import date
from fastapi import Request, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
from io import BytesIO
import openpyxl

from . import router, templates, handle_exceptions
from ..domain import SaldoContaCreate, SaldoContaUpdate
from ..services import (
    list_saldos_conta,
    get_saldo_conta,
    create_saldo_conta,
    update_saldo_conta,
    delete_saldo_conta,
    import_saldos_service,
    list_contas_bancarias,
)


@router.get('/saldos-bancarios')
@router.post('/saldos-bancarios')
@handle_exceptions
async def saldos_bancarios(request: Request):
    """List bank balances with optional filtering."""
    seq_conta = None
    data_inicio = None
    data_fim = None
    
    if request.method == 'POST':
        form = await request.form()
        conta_str = form.get('seq_conta')
        inicio_str = form.get('data_inicio')
        fim_str = form.get('data_fim')
        
        if conta_str:
            seq_conta = int(conta_str)
        if inicio_str:
            data_inicio = date.fromisoformat(inicio_str)
        if fim_str:
            data_fim = date.fromisoformat(fim_str)
    
    # Get filtered balances
    saldos = list_saldos_conta(
        seq_conta=seq_conta,
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    # Get all active bank accounts for filters and form
    contas_orm = list_contas_bancarias()
    contas = [
        {
            'seq_conta': c.seq_conta,
            'cod_banco': c.cod_banco,
            'num_agencia': c.num_agencia,
            'num_conta': c.num_conta,
            'dsc_conta': c.dsc_conta
        }
        for c in contas_orm
    ]
    
    return templates.TemplateResponse(
        'saldos_bancarios.html',
        {
            'request': request,
            'saldos': saldos,
            'contas': contas,
            'seq_conta_filter': seq_conta,
            'data_inicio_filter': data_inicio,
            'data_fim_filter': data_fim,
        }
    )


@router.post('/saldos-bancarios/adicionar', name='add_saldo_bancario')
@handle_exceptions
async def add_saldo_bancario(request: Request):
    """Create a new bank balance record."""
    form = await request.form()
    
    data = SaldoContaCreate(
        seq_conta=int(form['seq_conta']),
        dat_saldo=date.fromisoformat(form['dat_saldo']),
        val_saldo=float(form['val_saldo']),
    )
    
    create_saldo_conta(data)
    return RedirectResponse(request.url_for('saldos_bancarios'), status_code=303)


@router.post('/saldos-bancarios/{seq_saldo_conta}/editar', name='edit_saldo_bancario')
@handle_exceptions
async def edit_saldo_bancario(request: Request, seq_saldo_conta: int):
    """Update an existing bank balance record."""
    form = await request.form()
    
    data = SaldoContaUpdate(
        val_saldo=float(form['val_saldo']),
    )
    
    update_saldo_conta(seq_saldo_conta, data)
    return RedirectResponse(request.url_for('saldos_bancarios'), status_code=303)


@router.post('/saldos-bancarios/{seq_saldo_conta}/excluir', name='delete_saldo_bancario')
@handle_exceptions
async def delete_saldo_bancario(request: Request, seq_saldo_conta: int):
    """Delete a bank balance record."""
    delete_saldo_conta(seq_saldo_conta)
    return RedirectResponse(request.url_for('saldos_bancarios'), status_code=303)


@router.post('/saldos-bancarios/importar', name='import_saldos_bancarios')
@handle_exceptions
async def import_saldos_bancarios(file: UploadFile = File(...)):
    """Import multiple bank balance records from a CSV or XLSX file."""
    filename = file.filename or ''
    content = await file.read()
    
    result = import_saldos_service(content, filename)
    print(f"Relatório de Importação de Saldos: {result}")
    
    return RedirectResponse('/saldos-bancarios', status_code=303)


@router.get('/saldos-bancarios/template-xlsx', name='download_saldos_template')
@handle_exceptions
async def download_saldos_template():
    """Return an XLSX template for bulk bank balance import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Saldos"
    
    # Headers
    ws.append(["Data", "Conta", "Valor"])
    
    # Example rows
    exemplos = [
        (date(2025, 1, 1), "001/12345/123456-7", 150000.00),
        (date(2025, 1, 2), "001/12345/123456-7", 152000.00),
        (date(2025, 1, 1), "237/67890/987654-3", 80000.00),
    ]
    for e in exemplos:
        ws.append(list(e))
    
    # Format instructions
    ws.append([])
    ws.append(["INSTRUÇÕES:"])
    ws.append(["- Data: formato AAAA-MM-DD"])
    ws.append(["- Conta: formato Banco/Agência/Número (ex: 001/12345/123456-7)"])
    ws.append(["- Valor: número decimal (ex: 150000.00)"])
    
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename=saldos_bancarios_template.xlsx'
    }
    
    return StreamingResponse(
        stream,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers,
    )
