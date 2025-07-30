from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates, handle_exceptions
from ..domain import AlertaCreate, AlertaUpdate
from ..services import (
    list_alertas,
    create_alerta,
    update_alerta,
    delete_alerta,
)
from ..repositories import AlertaRepository

@router.get('/alertas')
@handle_exceptions
async def alertas(request: Request):
    regras, _ = list_alertas()
    return templates.TemplateResponse('alertas.html', {'request': request, 'regras': regras})

@router.get('/alertas/novo')
@handle_exceptions
async def novo_alerta(request: Request):
    _, qualificadores = list_alertas()
    return templates.TemplateResponse('alertas_novo.html', {'request': request, 'qualificadores': qualificadores})

@router.post('/alertas/novo')
@handle_exceptions
async def criar_alerta(request: Request):
    form = await request.form()
    data = AlertaCreate(
        nom_alerta=form.get('nom_alerta'),
        metric=form.get('metric'),
        seq_qualificador=form.get('seq_qualificador') or None,
        logic=form.get('logic'),
        valor=form.get('valor') or None,
        period=form.get('period') or None,
        notif_system='S' if form.get('notif_system') else 'N',
        notif_email='S' if form.get('notif_email') else 'N',
    )
    create_alerta(data)
    return RedirectResponse(request.url_for('alertas'), status_code=303)


@router.get('/alertas/edit/{seq_alerta}')
@handle_exceptions
async def edit_alerta(request: Request, seq_alerta: int):
    repo = AlertaRepository()
    alerta = repo.get(seq_alerta)
    _, qualificadores = list_alertas(repo)
    return templates.TemplateResponse(
        'alertas_edit.html',
        {'request': request, 'alerta': alerta, 'qualificadores': qualificadores},
    )


@router.post('/alertas/edit/{seq_alerta}', name='update_alerta')
@handle_exceptions
async def update_alerta_route(request: Request, seq_alerta: int):
    form = await request.form()
    data = AlertaUpdate(
        nom_alerta=form.get('nom_alerta'),
        metric=form.get('metric'),
        seq_qualificador=form.get('seq_qualificador') or None,
        logic=form.get('logic'),
        valor=form.get('valor') or None,
        period=form.get('period') or None,
        notif_system='S' if form.get('notif_system') else 'N',
        notif_email='S' if form.get('notif_email') else 'N',
    )
    update_alerta(seq_alerta, data)
    return RedirectResponse(request.url_for('alertas'), status_code=303)


@router.post('/alertas/delete/{seq_alerta}', name='delete_alerta')
@handle_exceptions
async def delete_alerta_route(request: Request, seq_alerta: int):
    delete_alerta(seq_alerta)
    return RedirectResponse(request.url_for('alertas'), status_code=303)

