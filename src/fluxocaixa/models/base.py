from sqlalchemy import create_engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    scoped_session,
    Query,
)
from fastapi import HTTPException

from ..config import Config


engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

Base = declarative_base()
Base.query = SessionLocal.query_property()


def _query_get_or_404(self: Query, ident, description=None):
    obj = self.get(ident)
    if obj is None:
        if description is None:
            model = self.column_descriptions[0]["type"].__name__
            description = f"{model} not found"
        raise HTTPException(status_code=404, detail=description)
    return obj


Query.get_or_404 = _query_get_or_404


class _DB:
    """Simple helper to mimic the minimal interface of Flask-SQLAlchemy."""

    def __init__(self):
        self.session = SessionLocal

    def create_all(self):
        Base.metadata.create_all(bind=engine)

    def drop_all(self):
        Base.metadata.drop_all(bind=engine)


db = _DB()


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

