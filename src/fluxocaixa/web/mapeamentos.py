from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates
from ..domain import MapeamentoCreate
from ..services import (
    list_mapeamentos,
    create_mapeamento,
    update_mapeamento,
    delete_mapeamento,
)
from ..repositories import MapeamentoRepository


@router.get('/mapeamentos')
async def mapeamentos(request: Request):
    status_filter = request.query_params.get('status', 'A')
    tipo_filter = request.query_params.get('tipo', '')
    mapeamentos, qualificadores = list_mapeamentos()
    if status_filter:
        mapeamentos = [m for m in mapeamentos if m.ind_status == status_filter]
    if tipo_filter:
        if tipo_filter == 'receita':
            mapeamentos = [m for m in mapeamentos if m.qualificador.num_qualificador.startswith('1')]
        elif tipo_filter == 'despesa':
            mapeamentos = [m for m in mapeamentos if m.qualificador.num_qualificador.startswith('2')]
    return templates.TemplateResponse(
        'mapeamentos.html',
        {
            'request': request,
            'mapeamentos': mapeamentos,
            'qualificadores': qualificadores,
            'status_filter': status_filter,
            'tipo_filter': tipo_filter,
        },
    )


@router.post('/mapeamentos/add')
async def add_mapeamento(request: Request):
    form = await request.form()
    data = MapeamentoCreate(
        seq_qualificador=int(form.get('seq_qualificador')),
        dsc_mapeamento=form.get('dsc_mapeamento'),
        txt_condicao=form.get('txt_condicao'),
    )
    create_mapeamento(data)
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.post('/mapeamentos/edit/{seq_mapeamento}')
async def edit_mapeamento(request: Request, seq_mapeamento: int):
    form = await request.form()
    data = MapeamentoCreate(
        seq_qualificador=int(form.get('seq_qualificador')),
        dsc_mapeamento=form.get('dsc_mapeamento'),
        txt_condicao=form.get('txt_condicao'),
    )
    update_mapeamento(seq_mapeamento, data)
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.post('/mapeamentos/delete/{seq_mapeamento}', name='delete_mapeamento')
async def delete_mapeamento_route(request: Request, seq_mapeamento: int):
    delete_mapeamento(seq_mapeamento)
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.get('/mapeamentos/get/{seq_mapeamento}')
async def get_mapeamento(seq_mapeamento: int):
    repo = MapeamentoRepository()
    mapeamento = repo.get(seq_mapeamento)
    return {
        'seq_mapeamento': mapeamento.seq_mapeamento,
        'seq_qualificador': mapeamento.seq_qualificador,
        'dsc_mapeamento': mapeamento.dsc_mapeamento,
        'txt_condicao': mapeamento.txt_condicao or '',
        'ind_status': mapeamento.ind_status,
    }
