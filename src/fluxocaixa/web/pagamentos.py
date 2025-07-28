from datetime import date

from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates
from ..models import db, Pagamento, Orgao


@router.get('/pagamentos')
async def pagamentos(request: Request):
    pagamentos = Pagamento.query.order_by(Pagamento.dat_pagamento.desc()).all()
    orgaos = Orgao.query.all()
    return templates.TemplateResponse('pagamentos.html', {'request': request, 'pagamentos': pagamentos, 'orgaos': orgaos})


@router.post('/pagamentos/add')
async def add_pagamento(request: Request):
    form = await request.form()
    dat = form.get('dat_pagamento')
    orgao = form.get('cod_orgao')
    valor = form.get('val_pagamento')
    desc = form.get('dsc_pagamento')
    pag = Pagamento(
        dat_pagamento=date.fromisoformat(dat),
        cod_orgao=orgao,
        val_pagamento=valor,
        dsc_pagamento=desc,
    )
    db.session.add(pag)
    db.session.commit()
    return RedirectResponse(request.url_for('pagamentos'), status_code=303)
