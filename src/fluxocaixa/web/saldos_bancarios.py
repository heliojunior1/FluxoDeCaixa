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
    """List bank balances with optional filtering and pagination."""
    seq_conta = None
    data_inicio = None
    data_fim = None
    page = 1
    per_page = 50
    sort_by = 'dat_saldo'
    sort_order = 'desc'
    
    if request.method == 'POST':
        form = await request.form()
        conta_str = form.get('seq_conta')
        inicio_str = form.get('data_inicio')
        fim_str = form.get('data_fim')
        page_str = form.get('page')
        sort_by = form.get('sort_by', 'dat_saldo')
        sort_order = form.get('sort_order', 'desc')
        
        if conta_str:
            seq_conta = int(conta_str)
        if inicio_str:
            data_inicio = date.fromisoformat(inicio_str)
        if fim_str:
            data_fim = date.fromisoformat(fim_str)
        if page_str:
            page = int(page_str)
    else:
        # GET request - check query params
        page_str = request.query_params.get('page')
        sort_by = request.query_params.get('sort_by', 'dat_saldo')
        sort_order = request.query_params.get('sort_order', 'desc')
        if page_str:
            page = int(page_str)
    
    # Get filtered balances with pagination
    saldos, total_count = list_saldos_conta(
        seq_conta=seq_conta,
        data_inicio=data_inicio,
        data_fim=data_fim,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
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
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'sort_by': sort_by,
            'sort_order': sort_order,
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
    
    saldo, error = create_saldo_conta(data)
    
    if error:
        # Get data for re-rendering the page with error message
        saldos, total_count = list_saldos_conta()
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
        
        total_pages = (total_count + 50 - 1) // 50 if total_count > 0 else 1
        
        return templates.TemplateResponse(
            'saldos_bancarios.html',
            {
                'request': request,
                'saldos': saldos,
                'contas': contas,
                'seq_conta_filter': None,
                'data_inicio_filter': None,
                'data_fim_filter': None,
                'error_message': error,
                'page': 1,
                'per_page': 50,
                'total_count': total_count,
                'total_pages': total_pages,
                'sort_by': 'dat_saldo',
                'sort_order': 'desc',
            }
        )
    
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
async def import_saldos_bancarios(request: Request, file: UploadFile = File(...)):
    """Import multiple bank balance records from a CSV or XLSX file."""
    filename = file.filename or ''
    content = await file.read()
    
    result = import_saldos_service(content, filename)
    print(f"Relatório de Importação de Saldos: {result}")
    
    # Build message for UI
    sucesso = result.get('sucesso', 0)
    erros = result.get('erros', [])
    
    success_message = None
    error_message = None
    
    if sucesso > 0:
        success_message = f"{sucesso} registro(s) importado(s) com sucesso!"
    
    if erros:
        error_message = "Erros na importação:\n• " + "\n• ".join(erros)
    
    if not sucesso and not erros:
        error_message = "Nenhum registro foi importado."
    
    # Get data for re-rendering the page with messages
    saldos, total_count = list_saldos_conta()
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
    
    total_pages = (total_count + 50 - 1) // 50 if total_count > 0 else 1
    
    return templates.TemplateResponse(
        'saldos_bancarios.html',
        {
            'request': request,
            'saldos': saldos,
            'contas': contas,
            'seq_conta_filter': None,
            'data_inicio_filter': None,
            'data_fim_filter': None,
            'success_message': success_message,
            'error_message': error_message,
            'page': 1,
            'per_page': 50,
            'total_count': total_count,
            'total_pages': total_pages,
            'sort_by': 'dat_saldo',
            'sort_order': 'desc',
        }
    )


@router.get('/saldos-bancarios/template-xlsx', name='download_saldos_template')
@handle_exceptions
async def download_saldos_template():
    """Return an XLSX template for bulk bank balance import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Saldos"
    
    # Headers
    ws.append(["Data", "Conta", "Valor"])
    
    # Get real accounts from database for examples
    contas_orm = list_contas_bancarias()
    
    if contas_orm:
        # Use real accounts in examples
        for i, conta in enumerate(contas_orm[:3]):  # Max 3 examples
            conta_str = f"{conta.cod_banco}/{conta.num_agencia}/{conta.num_conta}"
            example_date = date(2025, 1, i + 1)
            example_value = 100000.00 + (i * 50000)
            ws.append([example_date, conta_str, example_value])
    else:
        # Fallback to placeholder examples if no accounts exist
        ws.append([date(2025, 1, 1), "001/12345/123456-7", 150000.00])
        ws.append([date(2025, 1, 2), "001/12345/123456-7", 152000.00])
    
    # Format instructions
    ws.append([])
    ws.append(["INSTRUÇÕES:"])
    ws.append(["- Data: formato AAAA-MM-DD ou DD/MM/AAAA"])
    ws.append(["- Conta: formato Banco/Agência/Número (use as contas acima como referência)"])
    ws.append(["- Valor: número decimal (ex: 150000.00)"])
    ws.append(["- Apague as linhas de exemplo antes de importar seus dados"])
    
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
