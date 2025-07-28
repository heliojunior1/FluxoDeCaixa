from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates
from ..models import db, Mapeamento, Qualificador


@router.get('/mapeamentos')
async def mapeamentos(request: Request):
    status_filter = request.query_params.get('status', 'A')
    tipo_filter = request.query_params.get('tipo', '')
    query = Mapeamento.query.join(Qualificador)
    if status_filter:
        query = query.filter(Mapeamento.ind_status == status_filter)
    if tipo_filter:
        if tipo_filter == 'receita':
            query = query.filter(Qualificador.num_qualificador.startswith('1'))
        elif tipo_filter == 'despesa':
            query = query.filter(Qualificador.num_qualificador.startswith('2'))
    mapeamentos = query.order_by(Mapeamento.dat_inclusao.desc()).all()
    qualificadores = Qualificador.query.filter_by(ind_status='A').order_by(Qualificador.num_qualificador).all()
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
    seq_qualificador = form.get('seq_qualificador')
    desc = form.get('dsc_mapeamento')
    condicao = form.get('txt_condicao')
    mapeamento = Mapeamento(
        seq_qualificador=seq_qualificador,
        dsc_mapeamento=desc,
        txt_condicao=condicao,
        ind_status='A',
    )
    db.session.add(mapeamento)
    db.session.commit()
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.post('/mapeamentos/edit/{seq_mapeamento}')
async def edit_mapeamento(request: Request, seq_mapeamento: int):
    form = await request.form()
    mapeamento = Mapeamento.query.get_or_404(seq_mapeamento)
    mapeamento.seq_qualificador = form.get('seq_qualificador')
    mapeamento.dsc_mapeamento = form.get('dsc_mapeamento')
    mapeamento.txt_condicao = form.get('txt_condicao')
    db.session.commit()
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.post('/mapeamentos/delete/{seq_mapeamento}')
async def delete_mapeamento(request: Request, seq_mapeamento: int):
    mapeamento = Mapeamento.query.get_or_404(seq_mapeamento)
    mapeamento.ind_status = 'I'
    db.session.commit()
    return RedirectResponse(request.url_for('mapeamentos'), status_code=303)


@router.get('/mapeamentos/get/{seq_mapeamento}')
async def get_mapeamento(seq_mapeamento: int):
    mapeamento = Mapeamento.query.get_or_404(seq_mapeamento)
    return {
        'seq_mapeamento': mapeamento.seq_mapeamento,
        'seq_qualificador': mapeamento.seq_qualificador,
        'dsc_mapeamento': mapeamento.dsc_mapeamento,
        'txt_condicao': mapeamento.txt_condicao or '',
        'ind_status': mapeamento.ind_status,
    }
