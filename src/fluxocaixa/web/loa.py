"""Rotas web para gestão da LOA (Lei Orçamentária Anual)."""

import io
import csv
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import Request, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse

from . import router, templates, handle_exceptions
from ..models import Loa, Qualificador
from ..models.base import db

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ==================== Listagem ====================

@router.get('/loa')
@handle_exceptions
async def loa_list(request: Request):
    """Página principal da LOA com listagem e formulários."""
    ano_filtro = request.query_params.get('ano', None)

    query = Loa.query.filter_by(ind_status='A').order_by(Loa.num_ano.desc(), Loa.seq_qualificador)
    if ano_filtro:
        query = query.filter(Loa.num_ano == int(ano_filtro))

    registros = query.all()

    # Anos disponíveis para filtro
    anos_disponiveis = sorted(
        set(r.num_ano for r in Loa.query.filter_by(ind_status='A').all()),
        reverse=True,
    )

    # Qualificadores folha (sem filhos ativos) para o form manual
    todos_qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()
    qualificadores_folha = [q for q in todos_qualificadores if q.is_folha()]

    # Totais por ano
    totais = {}
    for r in registros:
        totais[r.num_ano] = totais.get(r.num_ano, Decimal('0')) + r.val_loa

    return templates.TemplateResponse(
        'loa.html',
        {
            'request': request,
            'registros': registros,
            'anos_disponiveis': anos_disponiveis,
            'ano_filtro': int(ano_filtro) if ano_filtro else None,
            'qualificadores': qualificadores_folha,
            'totais': totais,
            'has_openpyxl': HAS_OPENPYXL,
        },
    )


# ==================== Adicionar Manual ====================

@router.post('/loa/add')
@handle_exceptions
async def loa_add(request: Request):
    """Adiciona um registro LOA manualmente."""
    form = await request.form()
    num_ano = int(form.get('num_ano'))
    seq_qualificador = int(form.get('seq_qualificador'))
    val_loa = Decimal(form.get('val_loa', '0').replace('.', '').replace(',', '.'))

    # Verificar duplicidade (mesmo ano + qualificador)
    existente = Loa.query.filter_by(
        num_ano=num_ano,
        seq_qualificador=seq_qualificador,
        ind_status='A',
    ).first()

    if existente:
        existente.val_loa = val_loa
        existente.dat_inclusao = date.today()
    else:
        db.session.add(Loa(
            num_ano=num_ano,
            seq_qualificador=seq_qualificador,
            val_loa=val_loa,
        ))

    db.session.commit()
    return RedirectResponse(request.url_for('loa_list') + f'?ano={num_ano}', status_code=303)


# ==================== Excluir ====================

@router.post('/loa/delete/{seq_loa}')
@handle_exceptions
async def loa_delete(request: Request, seq_loa: int):
    """Exclui (inativa) um registro LOA."""
    registro = Loa.query.get_or_404(seq_loa)
    registro.ind_status = 'I'
    db.session.commit()
    return RedirectResponse(request.url_for('loa_list'), status_code=303)


# ==================== Importar CSV / Excel ====================

@router.post('/loa/importar')
@handle_exceptions
async def loa_importar(request: Request, arquivo: UploadFile = File(...), ano_import: int = Form(...)):
    """Importa registros LOA de um arquivo CSV ou Excel (.xlsx).
    
    Formato esperado (CSV):
    qualificador,valor
    ICMS,850000000.00
    IPVA,120000000.00
    
    Ou com código numérico:
    num_qualificador,valor
    1.0.0,850000000.00
    """
    if not arquivo.filename:
        return JSONResponse({'error': 'Nenhum arquivo enviado'}, status_code=400)

    conteudo = await arquivo.read()
    extensao = arquivo.filename.lower().rsplit('.', 1)[-1] if '.' in arquivo.filename else ''

    linhas_importadas = 0
    linhas_erro = []

    if extensao == 'csv':
        linhas_importadas, linhas_erro = _importar_csv(conteudo, ano_import)
    elif extensao in ('xlsx', 'xls'):
        if not HAS_OPENPYXL:
            return JSONResponse(
                {'error': 'Pacote openpyxl não instalado. Use CSV ou instale: pip install openpyxl'},
                status_code=400,
            )
        linhas_importadas, linhas_erro = _importar_excel(conteudo, ano_import)
    else:
        return JSONResponse({'error': f'Formato não suportado: .{extensao}. Use .csv ou .xlsx'}, status_code=400)

    db.session.commit()

    msg = f'{linhas_importadas} registro(s) importado(s) com sucesso para LOA {ano_import}.'
    if linhas_erro:
        msg += f' {len(linhas_erro)} erro(s): ' + '; '.join(linhas_erro[:5])

    return RedirectResponse(request.url_for('loa_list') + f'?ano={ano_import}&msg={msg}', status_code=303)


def _importar_csv(conteudo: bytes, ano: int) -> tuple:
    """Processa arquivo CSV e importa registros LOA."""
    importados = 0
    erros = []

    texto = conteudo.decode('utf-8-sig')  # utf-8 com BOM
    reader = csv.DictReader(io.StringIO(texto), delimiter=';')

    # Fallback para vírgula se não houver campos
    if not reader.fieldnames or len(reader.fieldnames) <= 1:
        reader = csv.DictReader(io.StringIO(texto), delimiter=',')

    for i, row in enumerate(reader, 2):
        try:
            qualificador_ref = (
                row.get('qualificador') or row.get('Qualificador') or
                row.get('num_qualificador') or row.get('QUALIFICADOR') or
                row.get('dsc_qualificador') or ''
            ).strip()

            valor_str = (
                row.get('valor') or row.get('Valor') or
                row.get('val_loa') or row.get('VALOR') or '0'
            ).strip().replace('.', '').replace(',', '.')

            if not qualificador_ref:
                erros.append(f'Linha {i}: qualificador vazio')
                continue

            valor = Decimal(valor_str)
            qualificador = _encontrar_qualificador(qualificador_ref)

            if not qualificador:
                erros.append(f'Linha {i}: qualificador "{qualificador_ref}" não encontrado')
                continue

            _upsert_loa(ano, qualificador.seq_qualificador, valor)
            importados += 1

        except (InvalidOperation, ValueError) as e:
            erros.append(f'Linha {i}: valor inválido ({e})')
        except Exception as e:
            erros.append(f'Linha {i}: {str(e)[:50]}')

    return importados, erros


def _importar_excel(conteudo: bytes, ano: int) -> tuple:
    """Processa arquivo Excel (.xlsx) e importa registros LOA."""
    importados = 0
    erros = []

    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return 0, ['Arquivo vazio ou sem dados']

    # Primeira linha = cabeçalho
    headers = [str(h).strip().lower() if h else '' for h in rows[0]]

    col_qual = None
    col_val = None
    for idx, h in enumerate(headers):
        if h in ('qualificador', 'num_qualificador', 'dsc_qualificador'):
            col_qual = idx
        if h in ('valor', 'val_loa'):
            col_val = idx

    if col_qual is None or col_val is None:
        return 0, ['Cabeçalhos não encontrados. Use: qualificador, valor']

    for i, row in enumerate(rows[1:], 2):
        try:
            qualificador_ref = str(row[col_qual]).strip() if row[col_qual] else ''
            valor_raw = row[col_val]

            if not qualificador_ref:
                erros.append(f'Linha {i}: qualificador vazio')
                continue

            if isinstance(valor_raw, (int, float)):
                valor = Decimal(str(valor_raw))
            else:
                valor = Decimal(str(valor_raw).strip().replace('.', '').replace(',', '.'))

            qualificador = _encontrar_qualificador(qualificador_ref)
            if not qualificador:
                erros.append(f'Linha {i}: qualificador "{qualificador_ref}" não encontrado')
                continue

            _upsert_loa(ano, qualificador.seq_qualificador, valor)
            importados += 1

        except Exception as e:
            erros.append(f'Linha {i}: {str(e)[:50]}')

    wb.close()
    return importados, erros


def _encontrar_qualificador(ref: str) -> Qualificador | None:
    """Busca qualificador por num_qualificador ou dsc_qualificador (case-insensitive)."""
    from sqlalchemy import func

    q = Qualificador.query.filter(
        Qualificador.num_qualificador == ref,
        Qualificador.ind_status == 'A',
    ).first()

    if not q:
        q = Qualificador.query.filter(
            func.lower(Qualificador.dsc_qualificador) == func.lower(ref),
            Qualificador.ind_status == 'A',
        ).first()

    return q


def _upsert_loa(ano: int, seq_qualificador: int, valor: Decimal):
    """Insere ou atualiza registro LOA (upsert por ano + qualificador)."""
    existente = Loa.query.filter_by(
        num_ano=ano,
        seq_qualificador=seq_qualificador,
        ind_status='A',
    ).first()

    if existente:
        existente.val_loa = valor
        existente.dat_inclusao = date.today()
    else:
        db.session.add(Loa(
            num_ano=ano,
            seq_qualificador=seq_qualificador,
            val_loa=valor,
        ))
