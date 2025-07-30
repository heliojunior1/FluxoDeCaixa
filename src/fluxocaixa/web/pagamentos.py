from datetime import date
from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates, handle_exceptions
from ..domain import PagamentoCreate
from ..services import list_pagamentos, create_pagamento


@router.get('/pagamentos')
@handle_exceptions
async def pagamentos(request: Request):
    pagamentos, orgaos = list_pagamentos()
    return templates.TemplateResponse(
        'pagamentos.html',
        {'request': request, 'pagamentos': pagamentos, 'orgaos': orgaos},
    )


@router.post('/pagamentos/add')
@handle_exceptions
async def add_pagamento(request: Request):
    form = await request.form()
    data = PagamentoCreate(
        dat_pagamento=date.fromisoformat(form.get('dat_pagamento')),
        cod_orgao=int(form.get('cod_orgao')),
        val_pagamento=form.get('val_pagamento'),
        dsc_pagamento=form.get('dsc_pagamento'),
    )
    create_pagamento(data)
    return RedirectResponse(request.url_for('pagamentos'), status_code=303)
