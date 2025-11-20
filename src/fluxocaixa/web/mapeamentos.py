from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates, handle_exceptions
from ..domain import MapeamentoCreate
from ..services import (
    list_mapeamentos,
    create_mapeamento,
    update_mapeamento,
    delete_mapeamento,
    get_mapeamento_by_id,
)
from ..repositories import MapeamentoRepository


@router.get('/mapeamentos')
@handle_exceptions
async def mapeamentos(request: Request):
    status_filter = request.query_params.get('status', 'A')
    tipo_filter = request.query_params.get('tipo', '')
    
    mapeamentos, qualificadores = list_mapeamentos(status=status_filter, tipo=tipo_filter)
    
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
@handle_exceptions
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
@handle_exceptions
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
@handle_exceptions
async def delete_mapeamento_route(request: Request, seq_mapeamento: int):
    delete_mapeamento(seq_mapeamento)
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.get('/mapeamentos/get/{seq_mapeamento}')
@handle_exceptions
async def get_mapeamento(seq_mapeamento: int):
    mapeamento = get_mapeamento_by_id(seq_mapeamento)
    return {
        'seq_mapeamento': mapeamento.seq_mapeamento,
        'seq_qualificador': mapeamento.seq_qualificador,
        'dsc_mapeamento': mapeamento.dsc_mapeamento,
        'txt_condicao': mapeamento.txt_condicao or '',
        'ind_status': mapeamento.ind_status,
    }
