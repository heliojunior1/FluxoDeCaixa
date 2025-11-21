from datetime import date, datetime
import calendar
import csv

from fastapi import Request, UploadFile, File
from fastapi.responses import RedirectResponse, StreamingResponse
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
)
from ..models import (
    db,
    Lancamento,
    Pagamento,
    Conferencia,
    Qualificador,
    TipoLancamento,
)
from ..services.seed import seed_data

@router.get('/')
@handle_exceptions
async def index(request: Request):
    """Página principal do sistema - apenas menu de navegação"""
    return templates.TemplateResponse('index.html', {'request': request})


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
    descricao = None
    tipo = None
    qualificador_folha = None

    if request.method == 'POST':
        form = await request.form()
        sd_str = form.get('start_date')
        ed_str = form.get('end_date')
        descricao = form.get('descricao')
        tipo_str = form.get('tipo')
        qual_str = form.get('qualificador_folha')

        if sd_str and ed_str:
            start_date = date.fromisoformat(sd_str)
            end_date = date.fromisoformat(ed_str)
        
        if tipo_str:
            tipo = int(tipo_str)
        
        if qual_str:
            qualificador_folha = int(qual_str)

    lancamentos = list_lancamentos(
        start_date=start_date,
        end_date=end_date,
        descricao=descricao,
        tipo=tipo,
        qualificador_folha=qualificador_folha
    )

    tipos = list_tipos_lancamento()
    origens = list_origens_lancamento()
    # Buscar apenas qualificadores folha (que não possuem filhos ativos)
    qualificadores = list_active_qualificadores()
    qualificadores_folha = [q for q in qualificadores if q.is_folha()]
    contas = list_contas_bancarias()

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
    ws.append(["Data", "Descrição", "Valor (R$)", "Tipo"])
    exemplos = [
        (date(2025, 1, 15), "ICMS", 700000.0, "Entrada"),
        (date(2025, 1, 15), "REPASSE MUNICÍPIOS", -420000.0, "Saída"),
        (date(2025, 2, 15), "FPE", 710000.0, "Entrada"),
        (date(2025, 2, 15), "FOLHA", -525000.0, "Saída"),
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


@router.get('/debug')
@handle_exceptions
async def debug():
    # TODO: This debug endpoint contains direct database access and should be:
    # 1. Moved to a dedicated debug/admin router
    # 2. Protected with authentication/authorization
    # 3. Removed in production environment
    # For now, keeping as-is for backwards compatibility
    output = []
    
    from ..repositories.tipo_lancamento_repository import TipoLancamentoRepository
    from ..repositories.lancamento_repository import LancamentoRepository
    from ..repositories.pagamento_repository import PagamentoRepository
    from ..repositories import qualificador_repository
    
    tipo_repo = TipoLancamentoRepository()
    lanc_repo = LancamentoRepository()
    pag_repo = PagamentoRepository()
    
    tipos = tipo_repo.list_all()
    output.append('<h2>Tipos de Lançamento:</h2>')
    for tipo in tipos:
        count, total = lanc_repo.get_stats_by_tipo(tipo.cod_tipo_lancamento)
        output.append(f'<p>{tipo.dsc_tipo_lancamento}: {count} registros, Total: {total:,.2f}</p>')
        
    count_pag, total_pag = pag_repo.get_stats()
    output.append('<h2>Pagamentos:</h2>')
    output.append(f'<p>Pagamentos: {count_pag} registros, Total: {total_pag:,.2f}</p>')
    
    qual_count = qualificador_repository.count_qualificadores()
    output.append('<h2>Qualificadores:</h2>')
    output.append(f'<p>Total qualificadores: {qual_count}</p>')
    
    qualificadores = qualificador_repository.get_qualificadores_limit(10)
    for q in qualificadores:
        output.append(f'<p>ID: {q.seq_qualificador}, Desc: {q.dsc_qualificador}</p>')
        
    output.append('<h2>Qualificadores de Despesa:</h2>')
    despesa_qualifs = ['FOLHA', 'REPASSE MUNICÍPIOS', 'PASEP']
    for desc in despesa_qualifs:
        q = qualificador_repository.get_qualificador_by_name(desc)
        if q:
            lanc_count = lanc_repo.count_by_qualificador(q.seq_qualificador)
            output.append(f'<p>{desc}: Encontrado (ID: {q.seq_qualificador}), Lançamentos: {lanc_count}</p>')
        else:
            output.append(f'<p>{desc}: Não encontrado</p>')
    output.append('<h2>Primeiros 10 Lançamentos:</h2>')
    sample_lanc = Lancamento.query.limit(10).all()
    for lanc in sample_lanc:
        output.append(f'<p>ID: {lanc.seq_lancamento}, Data: {lanc.dat_lancamento}, Valor: {lanc.val_lancamento}, Qualif: {lanc.seq_qualificador}, Tipo: {lanc.cod_tipo_lancamento}</p>')
    return HTMLResponse(''.join(output))
