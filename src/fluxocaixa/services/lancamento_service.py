from ..domain import LancamentoCreate, LancamentoOut
from ..repositories import LancamentoRepository
import csv
import openpyxl
from io import BytesIO, StringIO
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    db,
    Lancamento,
    Qualificador,
    TipoLancamento,
    OrigemLancamento,
    ContaBancaria,
    Conferencia,
)


def list_lancamentos(
    start_date: date | None = None,
    end_date: date | None = None,
    descricao: str | None = None,
    tipo: int | None = None,
    qualificador_folha: int | None = None,
    repo: LancamentoRepository | None = None
):
    repo = repo or LancamentoRepository()
    return repo.list(start_date, end_date, descricao, tipo, qualificador_folha)


def list_tipos_lancamento():
    return db.session.query(TipoLancamento).all()


def list_origens_lancamento():
    return db.session.query(OrigemLancamento).all()


def list_contas_bancarias():
    return db.session.query(ContaBancaria).filter_by(ind_status='A').all()


def list_conferencias():
    return db.session.query(Conferencia).order_by(Conferencia.dat_conferencia.desc()).all()


def create_lancamento(data: LancamentoCreate, repo: LancamentoRepository | None = None) -> LancamentoOut:
    repo = repo or LancamentoRepository()
    lanc = repo.create(data)
    return LancamentoOut(
        seq_lancamento=lanc.seq_lancamento,
        dat_lancamento=lanc.dat_lancamento,
        seq_qualificador=lanc.seq_qualificador,
        val_lancamento=lanc.val_lancamento,
        cod_tipo_lancamento=lanc.cod_tipo_lancamento,
        cod_origem_lancamento=lanc.cod_origem_lancamento,
        dsc_lancamento=None,
    seq_conta=lanc.seq_conta,
    )


def update_lancamento(ident: int, data: LancamentoCreate, repo: LancamentoRepository | None = None) -> LancamentoOut:
    repo = repo or LancamentoRepository()
    lanc = repo.update(ident, data)
    return LancamentoOut(
        seq_lancamento=lanc.seq_lancamento,
        dat_lancamento=lanc.dat_lancamento,
        seq_qualificador=lanc.seq_qualificador,
        val_lancamento=lanc.val_lancamento,
        cod_tipo_lancamento=lanc.cod_tipo_lancamento,
        cod_origem_lancamento=lanc.cod_origem_lancamento,
        dsc_lancamento=None,
    seq_conta=lanc.seq_conta,
    )


def delete_lancamento(ident: int, repo: LancamentoRepository | None = None):
    repo = repo or LancamentoRepository()
    repo.soft_delete(ident)


def import_lancamentos_service(
    content: bytes, filename: str, session: Session | None = None
) -> int:
    session = session or db.session
    rows: list[dict] = []
    
    if filename.lower().endswith('.csv'):
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(StringIO(text))
        for row in reader:
            rows.append({k.strip(): v for k, v in row.items()})
    elif filename.lower().endswith(('.xlsx', '.xls')):
        wb = openpyxl.load_workbook(BytesIO(content), data_only=True)
        ws = wb.active
        headers = [str(c).strip() if c else '' for c in next(ws.iter_rows(values_only=True))]
        for row in ws.iter_rows(min_row=2, values_only=True):
            data = {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
            rows.append(data)
    else:
        return 0

    default_origem = session.query(OrigemLancamento).first()
    count = 0

    def get_or_create_conta(banco, agencia, conta):
        if not (banco and agencia and conta):
            return None
        banco = str(banco).strip()
        agencia = str(agencia).strip()
        conta = str(conta).strip()
        c = (
            session.query(ContaBancaria).filter_by(
                cod_banco=banco, num_agencia=agencia, num_conta=conta
            ).first()
        )
        if not c:
            c = ContaBancaria(
                cod_banco=banco,
                num_agencia=agencia,
                num_conta=conta,
                dsc_conta=f"{banco}-{agencia}/{conta}",
            )
            session.add(c)
            session.flush()
        return c

    for item in rows:
        dat = item.get('Data') or item.get('dat_lancamento')
        desc = item.get('Descrição') or item.get('descricao')
        valor = item.get('Valor (R$)') or item.get('val_lancamento')
        tipo_raw = item.get('Tipo') or item.get('cod_tipo_lancamento')

        if not (dat and desc and valor and tipo_raw):
            continue

        if isinstance(dat, datetime):
            dat = dat.date()
        elif isinstance(dat, str):
            try:
                dat = date.fromisoformat(dat)
            except ValueError:
                continue

        qual = session.query(Qualificador).filter(func.lower(Qualificador.dsc_qualificador) == str(desc).lower()).first()
        if not qual:
            continue

        if isinstance(tipo_raw, str) and not tipo_raw.isdigit():
            tipo_obj = session.query(TipoLancamento).filter(func.lower(TipoLancamento.dsc_tipo_lancamento) == tipo_raw.lower()).first()
            if not tipo_obj:
                continue
            tipo = tipo_obj.cod_tipo_lancamento
        else:
            tipo = int(tipo_raw)

        origem = session.query(OrigemLancamento).filter(func.lower(OrigemLancamento.dsc_origem_lancamento) == str(desc).lower()).first() or default_origem

        # Detect optional bank fields
        banco = item.get('Banco') or item.get('banco') or item.get('BANCO')
        agencia = item.get('Agencia') or item.get('agencia') or item.get('AGENCIA')
        conta = item.get('Conta') or item.get('conta') or item.get('CONTA')
        conta_obj = get_or_create_conta(banco, agencia, conta)

        lanc = Lancamento(
            dat_lancamento=dat,
            seq_qualificador=qual.seq_qualificador,
            val_lancamento=float(valor),
            cod_tipo_lancamento=tipo,
            cod_origem_lancamento=origem.cod_origem_lancamento,
            ind_origem='A',
            cod_pessoa_inclusao=1,
            seq_conta=(conta_obj.seq_conta if conta_obj else None),
        )
        session.add(lanc)
        count += 1
    
    session.commit()
    return count
