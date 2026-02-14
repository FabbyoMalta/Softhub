import os

os.environ['DATABASE_URL'] = 'sqlite:///./test_softhub.db'
os.environ['IXC_MODE'] = 'mock'

from app.config import get_settings

get_settings.cache_clear()

from app.db import Base, engine, init_db


def pytest_sessionstart(session):
    Base.metadata.drop_all(bind=engine)
    init_db()
