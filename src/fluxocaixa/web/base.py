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
)
from ..models import (
    db,
    TipoLancamento,
    OrigemLancamento,
    Qualificador,
    Lancamento,
    Pagamento,
    Conferencia,
    Cenario,
    CenarioAjusteMensal,
)
from ..models import ContaBancaria
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
    lancamentos = list_lancamentos()
    query = [lan for lan in lancamentos if lan.ind_status == 'A']

    if request.method == 'POST':
        form = await request.form()
        start_date = form.get('start_date')
        end_date = form.get('end_date')
        descricao = form.get('descricao')
        tipo = form.get('tipo')
        qualificador_folha = form.get('qualificador_folha')

        if start_date and end_date:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
            query = [lan for lan in query if sd <= lan.dat_lancamento <= ed]
        if descricao:
            query = [
                lan
                for lan in query
                if descricao.lower() in lan.qualificador.dsc_qualificador.lower()
            ]
        if tipo:
            query = [lan for lan in query if str(lan.cod_tipo_lancamento) == str(tipo)]
        if qualificador_folha:
            query = [lan for lan in query if str(lan.seq_qualificador) == str(qualificador_folha)]

    # After filtering keep descending order by date
    lancamentos = sorted(query, key=lambda item: item.dat_lancamento, reverse=True)
    tipos = TipoLancamento.query.all()
    origens = OrigemLancamento.query.all()
    # Buscar apenas qualificadores folha (que não possuem filhos ativos)
    qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()
    qualificadores_folha = [q for q in qualificadores if q.is_folha()]

    return templates.TemplateResponse(
        'saldos.html',
        {
            'request': request,
            'lancamentos': lancamentos,
            'tipos': tipos,
            'origens': origens,
            'qualificadores': qualificadores,
            'qualificadores_folha': qualificadores_folha,
            'contas': ContaBancaria.query.filter_by(ind_status='A').all(),
        },
    )


@router.post('/saldos/add', name='add_lancamento')
@handle_exceptions
async def add_lancamento_route(request: Request):
    form = await request.form()
    data = LancamentoCreate(
        dat_lancamento=date.fromisoformat(form.get('dat_lancamento')),
        seq_qualificador=int(form.get('seq_qualificador')),
        val_lancamento=form.get('val_lancamento'),
        cod_tipo_lancamento=int(form.get('cod_tipo_lancamento')),
        cod_origem_lancamento=int(form.get('cod_origem_lancamento')),
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
    rows: list[dict] = []
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
        return RedirectResponse('/saldos', status_code=303)

    default_origem = OrigemLancamento.query.first()

    def get_or_create_conta(banco, agencia, conta):
        if not (banco and agencia and conta):
            return None
        banco = str(banco).strip()
        agencia = str(agencia).strip()
        conta = str(conta).strip()
        c = (
            ContaBancaria.query.filter_by(
                cod_banco=banco, num_agencia=agencia, num_conta=conta
            ).first()
        )
        if not c:
            c = ContaBancaria(
                cod_banco=banco,
                num_agencia=agencia,
                num_conta=conta,
                dsc_conta=f"{banco}-{agencia}/{conta}",
            )
            db.session.add(c)
            db.session.flush()
        return c
    for item in rows:
        dat = item.get('Data') or item.get('dat_lancamento')
        desc = item.get('Descrição') or item.get('descricao')
        valor = item.get('Valor (R$)') or item.get('val_lancamento')
        tipo_raw = item.get('Tipo') or item.get('cod_tipo_lancamento')

        if not (dat and desc and valor and tipo_raw):
            continue

        if isinstance(dat, datetime):
            dat = dat.date()
        elif isinstance(dat, str):
            dat = date.fromisoformat(dat)

        qual = Qualificador.query.filter(func.lower(Qualificador.dsc_qualificador) == str(desc).lower()).first()
        if not qual:
            continue

        if isinstance(tipo_raw, str) and not tipo_raw.isdigit():
            tipo_obj = TipoLancamento.query.filter(func.lower(TipoLancamento.dsc_tipo_lancamento) == tipo_raw.lower()).first()
            if not tipo_obj:
                continue
            tipo = tipo_obj.cod_tipo_lancamento
        else:
            tipo = int(tipo_raw)

        origem = OrigemLancamento.query.filter(func.lower(OrigemLancamento.dsc_origem_lancamento) == str(desc).lower()).first() or default_origem

        # Detect optional bank fields
        banco = item.get('Banco') or item.get('banco') or item.get('BANCO')
        agencia = item.get('Agencia') or item.get('agencia') or item.get('AGENCIA')
        conta = item.get('Conta') or item.get('conta') or item.get('CONTA')
        conta_obj = get_or_create_conta(banco, agencia, conta)

        lanc = Lancamento(
            dat_lancamento=dat,
            seq_qualificador=qual.seq_qualificador,
            val_lancamento=float(valor),
            cod_tipo_lancamento=tipo,
            cod_origem_lancamento=origem.cod_origem_lancamento,
            ind_origem='A',
            cod_pessoa_inclusao=1,
            seq_conta=(conta_obj.seq_conta if conta_obj else None),
        )
        db.session.add(lanc)
    db.session.commit()
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
        'Content-Disposition': 'attachment; filename="lancamentos_template.xlsx"'
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
    registros = Conferencia.query.order_by(Conferencia.dat_conferencia.desc()).all()
    return templates.TemplateResponse('conferencia.html', {'request': request, 'registros': registros})


@router.get('/projecoes')
@handle_exceptions
async def projecoes_menu(request: Request):
    """Menu principal das projeções."""
    return templates.TemplateResponse('projecoes_menu.html', {'request': request})


@router.get('/projecoes/cenarios')
@handle_exceptions
async def projecoes_cenarios(request: Request):
    cenarios = Cenario.query.order_by(Cenario.nom_cenario).all()
    qualificadores_receita = Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('1'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()
    qualificadores_despesa = Qualificador.query.filter(
        Qualificador.num_qualificador.startswith('2'),
        Qualificador.ind_status == 'A',
    ).order_by(Qualificador.num_qualificador).all()
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    return templates.TemplateResponse(
        'cenarios.html',
        {
            'request': request,
            'cenarios': cenarios,
            'qualificadores_receita': qualificadores_receita,
            'qualificadores_despesa': qualificadores_despesa,
            'meses_nomes': meses_nomes,
            'current_year': date.today().year,
        },
    )


@router.get('/projecoes/modelos')
@handle_exceptions
async def projecoes_modelos(request: Request):
    """Tela de projeções automáticas."""
    return templates.TemplateResponse('projecoes_modelos.html', {'request': request})


@router.get('/projecoes/get/{id}')
@handle_exceptions
async def get_cenario(id: int):
    cenario = Cenario.query.get_or_404(id)
    ajustes = CenarioAjusteMensal.query.filter_by(seq_cenario=id).all()
    ajustes_dict = {
        f"{a.ano}_{a.mes}_{a.seq_qualificador}": {
            'ano': a.ano,
            'mes': a.mes,
            'cod_tipo_ajuste': a.cod_tipo_ajuste,
            'val_ajuste': float(a.val_ajuste),
        }
        for a in ajustes
    }
    return {
        'seq_cenario': cenario.seq_cenario,
        'nom_cenario': cenario.nom_cenario,
        'dsc_cenario': cenario.dsc_cenario,
        'ajustes': ajustes_dict,
    }


@router.get('/projecoes/template-xlsx')
@handle_exceptions
async def download_cenario_template():
    """Return an XLSX template with all qualificadores listed."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "Periodo", "Valor", "Percentual"])
    qualificadores = (
        Qualificador.query.filter(
            Qualificador.ind_status == 'A',
            Qualificador.cod_qualificador_pai.isnot(None),
        )
        .order_by(Qualificador.dsc_qualificador)
        .all()
    )
    for i, q in enumerate(qualificadores, start=1):
        month = (i % 12) + 1
        valor = None
        percentual = None
        if q.dsc_qualificador.upper() == "ICMS":
            month = 1
            valor = 1200
        elif i % 2 == 0:
            valor = i * 100.0
        else:
            percentual = (i % 5 + 1) * 1.0
        ws.append([
            q.dsc_qualificador,
            f"{month:02d}/2025",
            valor,
            percentual,
        ])
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    headers = {
        'Content-Disposition': 'attachment; filename="cenario_template.xlsx"'
    }
    return StreamingResponse(
        stream,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers,
    )


@router.post('/projecoes/import-xlsx')
@handle_exceptions
async def import_cenario_xlsx(file: UploadFile = File(...)):
    """Parse an uploaded XLSX file and return adjustments mapping."""
    content = await file.read()
    wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
    ws = wb.active
    ajustes_dict = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        nome, periodo, valor, percentual = (list(row) + [None, None, None, None])[:4]
        if not nome or not periodo:
            continue
        qual = Qualificador.query.filter(
            func.lower(Qualificador.dsc_qualificador) == str(nome).lower()
        ).first()
        if not qual:
            continue
        # Parse period to year and month
        ano = None
        mes = None
        if hasattr(periodo, 'year') and hasattr(periodo, 'month'):
            ano = periodo.year
            mes = periodo.month
        else:
            pstr = str(periodo)
            if '/' in pstr:
                part = pstr.split('/')
                if len(part) == 2:
                    mes = int(part[0])
                    ano = int(part[1])
            elif '-' in pstr:
                part = pstr.split('-')
                if len(part) >= 2:
                    ano = int(part[0])
                    mes = int(part[1])
        if not ano or not mes:
            continue
        if percentual is not None:
            cod = 'P'
            val = float(percentual)
        elif valor is not None:
            cod = 'V'
            val = float(valor)
        else:
            continue
        key = f"{ano}_{mes}_{qual.seq_qualificador}"
        ajustes_dict[key] = {
            'ano': int(ano),
            'mes': int(mes),
            'cod_tipo_ajuste': cod,
            'val_ajuste': val,
        }
    return {'ajustes': ajustes_dict}


@router.post('/projecoes/add')
@handle_exceptions
async def add_cenario(request: Request):
    form = await request.form()
    nom_cenario = form.get('nom_cenario')
    dsc_cenario = form.get('dsc_cenario')
    ano = int(form.get('ano'))

    novo_cenario = Cenario(
        nom_cenario=nom_cenario,
        dsc_cenario=dsc_cenario,
        ind_status='A',
        cod_pessoa_inclusao=1,
    )
    db.session.add(novo_cenario)
    db.session.flush()
    for key, value in form.items():
        if key.startswith('val_ajuste_') and value:
            parts = key.split('_')
            mes = parts[2]
            seq_q = parts[3]
            seq_qualificador = int(seq_q)
            val_ajuste = float(value)
            cod_tipo_ajuste = form.get(f'cod_tipo_ajuste_{mes}_{seq_qualificador}', 'P')
            novo_ajuste = CenarioAjusteMensal(
                seq_cenario=novo_cenario.seq_cenario,
                seq_qualificador=seq_qualificador,
                ano=ano,
                mes=int(mes),
                cod_tipo_ajuste=cod_tipo_ajuste,
                val_ajuste=val_ajuste,
            )
            db.session.add(novo_ajuste)
    db.session.commit()
    return RedirectResponse(request.url_for('projecoes_cenarios'), status_code=303)


@router.get('/projecoes/edit/{id}')
@router.post('/projecoes/edit/{id}')
@handle_exceptions
async def edit_cenario(request: Request, id: int):
    cenario = Cenario.query.get_or_404(id)
    if request.method == 'POST':
        form = await request.form()
        cenario.nom_cenario = form['nom_cenario']
        cenario.dsc_cenario = form.get('dsc_cenario')
        ano = int(form.get('ano'))
        cenario.dat_alteracao = date.today()
        cenario.cod_pessoa_alteracao = 1
        CenarioAjusteMensal.query.filter_by(seq_cenario=id, ano=ano).delete()
        for key, value in form.items():
            if key.startswith('val_ajuste_') and value:
                parts = key.split('_')
                mes = parts[2]
                seq_q = parts[3]
                seq_qualificador = int(seq_q)
                cod_tipo_ajuste = form.get(f'cod_tipo_ajuste_{mes}_{seq_qualificador}')
                novo_ajuste = CenarioAjusteMensal(
                    seq_cenario=cenario.seq_cenario,
                    seq_qualificador=seq_qualificador,
                    ano=ano,
                    mes=int(mes),
                    cod_tipo_ajuste=cod_tipo_ajuste,
                    val_ajuste=float(value),
                )
                db.session.add(novo_ajuste)
        db.session.commit()
        return RedirectResponse(request.url_for('projecoes_cenarios'), status_code=303)
    qualificadores = Qualificador.query.filter(Qualificador.ind_status == 'A').order_by(Qualificador.num_qualificador).all()
    ajustes = {(a.ano, a.mes, a.seq_qualificador): a for a in cenario.ajustes_mensais}
    receitas = [q for q in qualificadores if q.tipo_fluxo == 'receita' and q.cod_qualificador_pai is not None]
    despesas = [q for q in qualificadores if q.tipo_fluxo == 'despesa' and q.cod_qualificador_pai is not None]
    ano = list(ajustes.keys())[0][0] if ajustes else date.today().year
    meses_nomes = {i: calendar.month_name[i].capitalize() for i in range(1, 13)}
    return templates.TemplateResponse(
        'cenario_edit.html',
        {
            'request': request,
            'cenario': cenario,
            'ajustes': ajustes,
            'receitas': receitas,
            'despesas': despesas,
            'ano': ano,
            'meses_nomes': meses_nomes,
        },
    )


@router.post('/projecoes/delete/{id}')
@handle_exceptions
async def delete_cenario(request: Request, id: int):
    cenario = Cenario.query.get_or_404(id)
    cenario.ind_status = 'I'
    cenario.dat_alteracao = date.today()
    cenario.cod_pessoa_alteracao = 1
    db.session.commit()
    return RedirectResponse(request.url_for('projecoes_cenarios'), status_code=303)


@router.get('/extrato-bancario')
@handle_exceptions
async def extrato_bancario(request: Request):
    lancamentos = db.session.query(
        Lancamento.dat_lancamento.label('data'),
        Qualificador.dsc_qualificador.label('descricao'),
        Lancamento.val_lancamento.label('valor'),
    ).join(Qualificador).all()
    pagamentos = db.session.query(
        Pagamento.dat_pagamento.label('data'),
        Pagamento.dsc_pagamento.label('descricao'),
        (-Pagamento.val_pagamento).label('valor'),
    ).all()
    movimentos = [
        {
            'data': lanc.data,
            'descricao': lanc.descricao,
            'valor': float(lanc.valor),
        }
        for lanc in lancamentos
    ] + [
        {
            'data': pag.data,
            'descricao': pag.descricao,
            'valor': float(pag.valor),
        }
        for pag in pagamentos
    ]
    movimentos.sort(key=lambda x: x['data'])
    saldo = 0
    for m in movimentos:
        saldo += m['valor']
        m['saldo'] = saldo
    return templates.TemplateResponse('extrato.html', {'request': request, 'movimentos': movimentos})


@router.get('/qualificadores')
@handle_exceptions
async def qualificadores(request: Request):
    qualificadores_raiz = Qualificador.query.filter_by(
        ind_status='A', cod_qualificador_pai=None
    ).order_by(Qualificador.num_qualificador).all()
    todos_qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()
    return templates.TemplateResponse(
        'qualificadores.html',
        {
            'request': request,
            'qualificadores': qualificadores_raiz,
            'todos_qualificadores': todos_qualificadores,
        },
    )


@router.post('/qualificadores/add')
@handle_exceptions
async def add_qualificador(request: Request):
    form = await request.form()
    num_qualif = form.get('num_qualificador')
    desc = form.get('dsc_qualificador')
    pai_id = form.get('cod_qualificador_pai')
    if not pai_id or pai_id == '':
        pai_id = None
    else:
        pai_id = int(pai_id)
    qualificador = Qualificador(
        num_qualificador=num_qualif,
        dsc_qualificador=desc,
        cod_qualificador_pai=pai_id,
    )
    db.session.add(qualificador)
    db.session.commit()
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)


@router.post('/qualificadores/edit/{seq_qualificador}')
@handle_exceptions
async def edit_qualificador(request: Request, seq_qualificador: int):
    form = await request.form()
    qualificador = Qualificador.query.get_or_404(seq_qualificador)
    qualificador.num_qualificador = form['num_qualificador']
    qualificador.dsc_qualificador = form['dsc_qualificador']
    pai_id = form.get('cod_qualificador_pai')
    if not pai_id or pai_id == '':
        qualificador.cod_qualificador_pai = None
    else:
        qualificador.cod_qualificador_pai = int(pai_id)
    db.session.commit()
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)


@router.post('/qualificadores/delete/{seq_qualificador}')
@handle_exceptions
async def delete_qualificador(request: Request, seq_qualificador: int):
    qualificador = Qualificador.query.get_or_404(seq_qualificador)
    qualificador.ind_status = 'I'
    db.session.commit()
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)


@router.get('/debug')
@handle_exceptions
async def debug():
    output = []
    tipos = TipoLancamento.query.all()
    output.append('<h2>Tipos de Lançamento:</h2>')
    for tipo in tipos:
        count = Lancamento.query.filter_by(cod_tipo_lancamento=tipo.cod_tipo_lancamento).count()
        total = (
            db.session.query(func.sum(Lancamento.val_lancamento))
            .filter_by(cod_tipo_lancamento=tipo.cod_tipo_lancamento)
            .scalar()
            or 0
        )
        output.append(f'<p>{tipo.dsc_tipo_lancamento}: {count} registros, Total: {total:,.2f}</p>')
    count_pag = Pagamento.query.count()
    total_pag = db.session.query(func.sum(Pagamento.val_pagamento)).scalar() or 0
    output.append('<h2>Pagamentos:</h2>')
    output.append(f'<p>Pagamentos: {count_pag} registros, Total: {total_pag:,.2f}</p>')
    qual_count = Qualificador.query.count()
    output.append('<h2>Qualificadores:</h2>')
    output.append(f'<p>Total qualificadores: {qual_count}</p>')
    qualificadores = Qualificador.query.limit(10).all()
    for q in qualificadores:
        output.append(f'<p>ID: {q.seq_qualificador}, Desc: {q.dsc_qualificador}</p>')
    output.append('<h2>Qualificadores de Despesa:</h2>')
    despesa_qualifs = ['FOLHA', 'REPASSE MUNICÍPIOS', 'PASEP']
    for desc in despesa_qualifs:
        q = Qualificador.query.filter_by(dsc_qualificador=desc).first()
        if q:
            lanc_count = Lancamento.query.filter_by(seq_qualificador=q.seq_qualificador).count()
            output.append(f'<p>{desc}: Encontrado (ID: {q.seq_qualificador}), Lançamentos: {lanc_count}</p>')
        else:
            output.append(f'<p>{desc}: NÃO ENCONTRADO</p>')
    output.append('<h2>Primeiros 10 Lançamentos:</h2>')
    sample_lanc = Lancamento.query.limit(10).all()
    for lanc in sample_lanc:
        output.append(f'<p>ID: {lanc.seq_lancamento}, Data: {lanc.dat_lancamento}, Valor: {lanc.val_lancamento}, Qualif: {lanc.seq_qualificador}, Tipo: {lanc.cod_tipo_lancamento}</p>')
    return '<br>'.join(output)
