"""Seed data for Conferencia."""

from datetime import date

from ...models import Conferencia
from ...models.base import db


def seed_conferencia(session=None):
    """Seed Conferencia records."""
    session = session or db.session

    if Conferencia.query.first():
        return  # Already seeded

    conferencia_data = [
        {
            'data': date(2025, 6, 17),
            'saldo_anterior': 568262058.81,
            'liberacoes': 0.00,
            'conf_liberacoes': 0.00,
            'soma_anter_liberacoes': 568262058.81,
            'pagamentos': 0.00,
            'conf_pagamentos': 0.00,
            'saldo_final': 568262058.81
        },
        {
            'data': date(2025, 6, 11),
            'saldo_anterior': 537524274.27,
            'liberacoes': 103672302.26,
            'conf_liberacoes': 103672302.26,
            'soma_anter_liberacoes': 578196242.69,
            'pagamentos': 16322223.28,
            'conf_pagamentos': 16322223.28,
            'saldo_final': 565242020.81
        },
        {
            'data': date(2025, 6, 10),
            'saldo_anterior': 519605479.27,
            'liberacoes': 81824500.48,
            'conf_liberacoes': 81824500.48,
            'soma_anter_liberacoes': 537524274.27,
            'pagamentos': 34971506.42,
            'conf_pagamentos': 34971506.42,
            'saldo_final': 537524274.27
        },
        {
            'data': date(2025, 6, 9),
            'saldo_anterior': 503024713.99,
            'liberacoes': 13733378.04,
            'conf_liberacoes': 13733378.04,
            'soma_anter_liberacoes': 394277502.03,
            'pagamentos': 91375376.76,
            'conf_pagamentos': 91375376.76,
            'saldo_final': 384596331.28
        },
        {
            'data': date(2025, 6, 6),
            'saldo_anterior': 510024713.99,
            'liberacoes': 0.00,
            'conf_liberacoes': 0.00,
            'soma_anter_liberacoes': 381024713.99,
            'pagamentos': 0.00,
            'conf_pagamentos': 0.00,
            'saldo_final': 381024713.99
        },
        {
            'data': date(2025, 6, 3),
            'saldo_anterior': 511024713.99,
            'liberacoes': 0.00,
            'conf_liberacoes': 0.00,
            'soma_anter_liberacoes': 381024713.99,
            'pagamentos': 0.00,
            'conf_pagamentos': 0.00,
            'saldo_final': 381024713.99
        },
        {
            'data': date(2025, 5, 7),
            'saldo_anterior': 497706837.99,
            'liberacoes': 315481715.45,
            'conf_liberacoes': 222029719.45,
            'soma_anter_liberacoes': 640176142.26,
            'pagamentos': 271854879.64,
            'conf_pagamentos': 271854879.64,
            'saldo_final': 497528837.99
        },
        {
            'data': date(2025, 4, 4),
            'saldo_anterior': 616759.50,
            'liberacoes': 78331415.91,
            'conf_liberacoes': 78331415.91,
            'soma_anter_liberacoes': 640176176.35,
            'pagamentos': 62376142.28,
            'conf_pagamentos': 62376142.28,
            'saldo_final': 597528837.47
        },
        {
            'data': date(2025, 4, 3),
            'saldo_anterior': 542017684.77,
            'liberacoes': 131773250.00,
            'conf_liberacoes': 131773250.00,
            'soma_anter_liberacoes': 434301447.30,
            'pagamentos': 53317634.39,
            'conf_pagamentos': 53317634.39,
            'saldo_final': 410624476.94
        },
        {
            'data': date(2025, 4, 2),
            'saldo_anterior': 502093936.77,
            'liberacoes': 131738200.00,
            'conf_liberacoes': 131738200.00,
            'soma_anter_liberacoes': 436350547.30,
            'pagamentos': 179956820.39,
            'conf_pagamentos': 179956820.39,
            'saldo_final': 473053165.04
        },
        {
            'data': date(2025, 3, 2),
            'saldo_anterior': 524803174.32,
            'liberacoes': 105302341.10,
            'conf_liberacoes': 105302341.10,
            'soma_anter_liberacoes': 430050547.30,
            'pagamentos': 72470350.48,
            'conf_pagamentos': 72470350.48,
            'saldo_final': 553033165.04
        },
        {
            'data': date(2025, 3, 1),
            'saldo_anterior': 524803174.32,
            'liberacoes': 0.00,
            'conf_liberacoes': 0.00,
            'soma_anter_liberacoes': 524803174.32,
            'pagamentos': 0.00,
            'conf_pagamentos': 0.00,
            'saldo_final': 524803174.32
        },
        {
            'data': date(2025, 2, 1),
            'saldo_anterior': 524803174.32,
            'liberacoes': 0.00,
            'conf_liberacoes': 0.00,
            'soma_anter_liberacoes': 524803174.32,
            'pagamentos': 0.00,
            'conf_pagamentos': 0.00,
            'saldo_final': 524803174.32
        }
    ]

    for dados in conferencia_data:
        conferencia = Conferencia(
            dat_conferencia=dados['data'],
            val_saldo_anterior=dados['saldo_anterior'],
            val_liberacoes=dados['liberacoes'],
            val_conf_liberacoes=dados['conf_liberacoes'],
            val_soma_anter_liberacoes=dados['soma_anter_liberacoes'],
            val_pagamentos=dados['pagamentos'],
            val_conf_pagamentos=dados['conf_pagamentos'],
            val_saldo_final=dados['saldo_final']
        )
        session.add(conferencia)

    session.commit()
