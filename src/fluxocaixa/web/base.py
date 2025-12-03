from datetime import date, datetime
import calendar
import csv

from fastapi import Request, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse, HTMLResponse
from io import BytesIO, StringIO
import openpyxl
from sqlalchemy import func

from . import router, templates, handle_exceptions
from ..domain import LancamentoCreate
from ..services import (
    list_lancamentos,
    create_lancamento,
    update_lancamento,
    delete_lancamento,
    import_lancamentos_service,
    list_tipos_lancamento,
    list_origens_lancamento,
    list_contas_bancarias,
    list_active_qualificadores,
    list_conferencias,
    list_alertas_ativos,
)
from ..models import db
from ..services.seed import seed_data

@router.get('/')
@handle_exceptions
async def index(request: Request):
    """Página principal do sistema - menu de navigação e alertas de gestão"""
    alertas = list_alertas_ativos()
    return templates.TemplateResponse('index.html', {
        'request': request,
        'alertas': alertas,
        'now': datetime.now
    })


@router.get('/init-db')
@handle_exceptions
async def init_db():
    """Initialize/reset the database with seed data"""
    try:
        db.create_all()
        from ..models.alerta import ensure_alerta_schema
        ensure_alerta_schema()
        seed_data()
        return "Database initialized successfully!"
    except Exception as e:
        return f"Error initializing database: {str(e)}"


@router.get('/recreate-db')
@handle_exceptions
async def recreate_db():
    """Recreate the database from scratch"""
    try:
        db.drop_all()
        db.create_all()
        from ..models.alerta import ensure_alerta_schema
        ensure_alerta_schema()
        seed_data()
        return "Database recreated successfully!"
    except Exception as e:
        return f"Error recreating database: {str(e)}"


@router.get('/saldos')
@router.post('/saldos')
@handle_exceptions
async def saldos(request: Request):
    start_date = None
    end_date = None
    tipo = None
    qualificador_folha = None
    seq_conta = None
    cod_origem = None
    page = 1
    per_page = 50
    sort_by = 'dat_lancamento'
    sort_order = 'desc'

    if request.method == 'POST':
        form = await request.form()
        sd_str = form.get('start_date')
        ed_str = form.get('end_date')
        tipo_str = form.get('tipo')
        qual_str = form.get('qualificador_folha')
        conta_str = form.get('seq_conta')
        origem_str = form.get('cod_origem')
        page_str = form.get('page')
        sort_by = form.get('sort_by', 'dat_lancamento')
        sort_order = form.get('sort_order', 'desc')

        if sd_str and ed_str:
            start_date = date.fromisoformat(sd_str)
            end_date = date.fromisoformat(ed_str)
        
        if tipo_str:
            tipo = int(tipo_str)
        
        if qual_str:
            qualificador_folha = int(qual_str)
        
        if conta_str:
            seq_conta = int(conta_str)
        
        if origem_str:
            cod_origem = int(origem_str)
        
        if page_str:
            page = int(page_str)
    else:
        # GET request - check query params
        page_str = request.query_params.get('page')
        sort_by = request.query_params.get('sort_by', 'dat_lancamento')
        sort_order = request.query_params.get('sort_order', 'desc')
        if page_str:
            page = int(page_str)

    lancamentos, total_count = list_lancamentos(
        start_date=start_date,
        end_date=end_date,
        tipo=tipo,
        qualificador_folha=qualificador_folha,
        seq_conta=seq_conta,
        cod_origem=cod_origem,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    tipos = list_tipos_lancamento()
    origens = list_origens_lancamento()
    # Buscar apenas qualificadores folha (que não possuem filhos ativos)
    qualificadores = list_active_qualificadores()
    qualificadores_folha = [q for q in qualificadores if q.is_folha()]
    contas = list_contas_bancarias()

    # Obter código da origem "Manual" para inserção automática
    origem_manual = next((o for o in origens if o.dsc_origem_lancamento == 'Manual'), None)
    cod_origem_manual = origem_manual.cod_origem_lancamento if origem_manual else 1

    return templates.TemplateResponse(
        'saldos.html',
        {
            'request': request,
            'lancamentos': lancamentos,
            'tipos': tipos,
            'origens': origens,
            'qualificadores': qualificadores,
            'qualificadores_folha': qualificadores_folha,
            'contas': contas,
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages,
            'sort_by': sort_by,
            'sort_order': sort_order,
            'cod_origem_manual': cod_origem_manual,
            'filtros': {
                'start_date': start_date.isoformat() if start_date else '',
                'end_date': end_date.isoformat() if end_date else '',
                'tipo': tipo or '',
                'qualificador_folha': qualificador_folha or '',
                'seq_conta': seq_conta or '',
                'cod_origem': cod_origem or '',
            },
        },
    )



@router.post('/saldos/add', name='add_lancamento')
@handle_exceptions
async def add_lancamento(request: Request):
    form = await request.form()
    data = LancamentoCreate(
        dat_lancamento=date.fromisoformat(form['dat_lancamento']),
        seq_qualificador=int(form['seq_qualificador']),
        val_lancamento=form['val_lancamento'],
        cod_tipo_lancamento=int(form['cod_tipo_lancamento']),
        cod_origem_lancamento=int(form['cod_origem_lancamento']),
        seq_conta=int(form.get('seq_conta')) if form.get('seq_conta') else None,
    )
    create_lancamento(data)
    return RedirectResponse(request.url_for('saldos'), status_code=303)


@router.post('/saldos/import')
@handle_exceptions
async def import_lancamentos(file: UploadFile = File(...)):
    """Import multiple Lancamento records from a CSV or XLSX file."""
    filename = file.filename or ''
    content = await file.read()
    
    result = import_lancamentos_service(content, filename)
    print(f"Relatório de Importação: {result}")
    
    return RedirectResponse('/saldos', status_code=303)


@router.get('/saldos/template-xlsx')
@handle_exceptions
async def download_lancamento_template():
    """Return an XLSX template for bulk Lancamento import."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Data", "Qualificador", "Valor (R$)", "Tipo", "Banco", "Agencia", "Conta"])
    exemplos = [
        (date(2025, 1, 15), "ICMS", 700000.0, "Entrada", "001", "0001", "123456-7"),
        (date(2025, 1, 15), "REPASSE MUNICÍPIOS", -420000.0, "Saída", "001", "0001", "123456-7"),
        (date(2025, 2, 15), "FPE", 710000.0, "Entrada", "341", "3200", "556677-8"),
        (date(2025, 2, 15), "FOLHA", -525000.0, "Saída", "237", "1234", "98765-4"),
    ]
    for e in exemplos:
        ws.append(list(e))
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename=lancamentos_template.xlsx'
    }
    return StreamingResponse(
        stream,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers,
    )


@router.post('/saldos/edit/{seq_lancamento}', name='update_lancamento')
@handle_exceptions
async def edit_lancamento_route(request: Request, seq_lancamento: int):
    form = await request.form()
    data = LancamentoCreate(
        dat_lancamento=date.fromisoformat(form['dat_lancamento']),
        seq_qualificador=int(form['seq_qualificador']),
        val_lancamento=form['val_lancamento'],
        cod_tipo_lancamento=int(form['cod_tipo_lancamento']),
        cod_origem_lancamento=int(form['cod_origem_lancamento']),
    seq_conta=int(form.get('seq_conta')) if form.get('seq_conta') else None,
    )
    update_lancamento(seq_lancamento, data)
    return RedirectResponse(request.url_for('saldos'), status_code=303)


@router.post('/saldos/delete/{seq_lancamento}', name='delete_lancamento')
@handle_exceptions
async def delete_lancamento_route(request: Request, seq_lancamento: int):
    delete_lancamento(seq_lancamento)
    return RedirectResponse(request.url_for('saldos'), status_code=303)


@router.get('/conferencia')
@handle_exceptions
async def conferencia(request: Request):
    registros = list_conferencias()
    return templates.TemplateResponse('conferencia.html', {'request': request, 'registros': registros})


