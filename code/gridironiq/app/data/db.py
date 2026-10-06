"""Engine and session management. Swappable for tests via make_session_factory."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.data.models import Base

DEFAULT_URL = os.environ.get("GRIDIRONIQ_DB_URL", "sqlite:///./gridironiq.db")


def make_engine(url: str = DEFAULT_URL):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, future=True)


def make_session_factory(url: str = DEFAULT_URL) -> sessionmaker[Session]:
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
