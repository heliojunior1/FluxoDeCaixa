from datetime import date
from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates
from ..models import db, Alerta, Qualificador

@router.get('/alertas')
async def alertas(request: Request):
    regras = Alerta.query.order_by(Alerta.nom_alerta).all()
    return templates.TemplateResponse('alertas.html', {'request': request, 'regras': regras})

@router.get('/alertas/novo')
async def novo_alerta(request: Request):
    qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.dsc_qualificador).all()
    return templates.TemplateResponse('alertas_novo.html', {'request': request, 'qualificadores': qualificadores})

@router.post('/alertas/novo')
async def criar_alerta(request: Request):
    form = await request.form()
    alerta = Alerta(
        nom_alerta=form.get('nom_alerta'),
        metric=form.get('metric'),
        seq_qualificador=form.get('seq_qualificador') or None,
        logic=form.get('logic'),
        valor=form.get('valor') or None,
        period=form.get('period') or None,
        emails=form.get('emails'),
        notif_system='S' if form.get('notif_system') else 'N',
        notif_email='S' if form.get('notif_email') else 'N',
        cod_pessoa_inclusao=1,
    )
    db.session.add(alerta)
    db.session.commit()
    return RedirectResponse(request.url_for('alertas'), status_code=303)


@router.get('/alertas/edit/{seq_alerta}')
async def edit_alerta(request: Request, seq_alerta: int):
    alerta = Alerta.query.get_or_404(seq_alerta)
    qualificadores = (
        Qualificador.query.filter_by(ind_status='A')
        .order_by(Qualificador.dsc_qualificador)
        .all()
    )
    return templates.TemplateResponse(
        'alertas_edit.html',
        {'request': request, 'alerta': alerta, 'qualificadores': qualificadores},
    )


@router.post('/alertas/edit/{seq_alerta}')
async def update_alerta(request: Request, seq_alerta: int):
    alerta = Alerta.query.get_or_404(seq_alerta)
    form = await request.form()
    alerta.nom_alerta = form.get('nom_alerta')
    alerta.metric = form.get('metric')
    alerta.seq_qualificador = form.get('seq_qualificador') or None
    alerta.logic = form.get('logic')
    alerta.valor = form.get('valor') or None
    alerta.period = form.get('period') or None
    alerta.emails = form.get('emails')
    alerta.notif_system = 'S' if form.get('notif_system') else 'N'
    alerta.notif_email = 'S' if form.get('notif_email') else 'N'
    alerta.dat_alteracao = date.today()
    alerta.cod_pessoa_alteracao = 1
    db.session.commit()
    return RedirectResponse(request.url_for('alertas'), status_code=303)


@router.post('/alertas/delete/{seq_alerta}')
async def delete_alerta(request: Request, seq_alerta: int):
    alerta = Alerta.query.get_or_404(seq_alerta)
    alerta.ind_status = 'I'
    alerta.dat_alteracao = date.today()
    alerta.cod_pessoa_alteracao = 1
    db.session.commit()
    return RedirectResponse(request.url_for('alertas'), status_code=303)

