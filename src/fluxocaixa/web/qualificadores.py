from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates, handle_exceptions
from ..services import (
    list_root_qualificadores,
    list_active_qualificadores,
    create_qualificador,
    update_qualificador,
    delete_qualificador_service,
    get_qualificador,
)

@router.get('/qualificadores')
@handle_exceptions
async def qualificadores(request: Request):
    qualificadores_raiz = list_root_qualificadores()
    todos_qualificadores = list_active_qualificadores()
    return templates.TemplateResponse(
        'qualificadores.html',
        {
            'request': request,
            'qualificadores': qualificadores_raiz,
            'todos_qualificadores': todos_qualificadores,
        },
    )


@router.post('/qualificadores/add', name='add_qualificador')
@handle_exceptions
async def add_qualificador_route(request: Request):
    form = await request.form()
    num_qualif = form.get('num_qualificador')
    desc = form.get('dsc_qualificador')
    pai_id = form.get('cod_qualificador_pai')
    
    cod_qualificador_pai = int(pai_id) if pai_id and pai_id != '' else None
    
    create_qualificador(num_qualif, desc, cod_qualificador_pai)
    
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)


@router.post('/qualificadores/edit/{seq_qualificador}')
@handle_exceptions
async def edit_qualificador_route(request: Request, seq_qualificador: int):
    form = await request.form()
    num_qualif = form['num_qualificador']
    desc = form['dsc_qualificador']
    pai_id = form.get('cod_qualificador_pai')
    
    cod_qualificador_pai = int(pai_id) if pai_id and pai_id != '' else None
    
    update_qualificador(seq_qualificador, num_qualif, desc, cod_qualificador_pai)
    
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)


@router.post('/qualificadores/delete/{seq_qualificador}', name='delete_qualificador')
@handle_exceptions
async def delete_qualificador_route(request: Request, seq_qualificador: int):
    delete_qualificador_service(seq_qualificador)
    return RedirectResponse(request.url_for('qualificadores'), status_code=303)
