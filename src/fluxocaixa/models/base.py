from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

from ..config import Config


engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))

Base = declarative_base()
Base.query = SessionLocal.query_property()


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

