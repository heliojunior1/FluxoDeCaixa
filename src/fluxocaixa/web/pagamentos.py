from datetime import date
from fastapi import Request
from fastapi.responses import RedirectResponse

from . import router, templates, handle_exceptions
from ..domain import PagamentoCreate
from ..services import list_pagamentos, create_pagamento


@router.get('/pagamentos')
@handle_exceptions
async def pagamentos(request: Request):
    pagamentos, orgaos, qualificadores = list_pagamentos()
    return templates.TemplateResponse(
        'pagamentos.html',
        {'request': request, 'pagamentos': pagamentos, 'orgaos': orgaos, 'qualificadores': qualificadores},
    )


@router.post('/pagamentos/add')
@handle_exceptions
async def add_pagamento(request: Request):
    form = await request.form()
    
    # Handle empty string for seq_qualificador
    seq_qualificador = form.get('seq_qualificador')
    if seq_qualificador == '' or seq_qualificador is None:
        seq_qualificador = None
    else:
        seq_qualificador = int(seq_qualificador)
    
    data = PagamentoCreate(
        dat_pagamento=date.fromisoformat(form.get('dat_pagamento')),
        cod_orgao=int(form.get('cod_orgao')),
        seq_qualificador=seq_qualificador,
        val_pagamento=form.get('val_pagamento'),
        dsc_pagamento=form.get('dsc_pagamento'),
    )
    create_pagamento(data)
    return RedirectResponse(request.url_for('pagamentos'), status_code=303)
