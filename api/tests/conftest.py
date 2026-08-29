"""Test fixtures.

The API tests run against a real MySQL database — the same engine production
uses — because half the things worth testing here (unique constraints, the
enum CHECKs, transaction boundaries) do not exist on SQLite. Each test runs
inside a transaction that is rolled back afterwards, so the tests do not have
to clean up after each other.

Set TEST_DATABASE_URL to point them somewhere. Without a reachable server the
API tests skip and the pure `app.core` tests still run.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

os.environ.setdefault("SECRET_KEY", "test-secret-not-used-anywhere-real")
os.environ.setdefault("ENV", "test")

DEFAULT_TEST_URL = (
    "mysql+pymysql://brikole:devpassword@127.0.0.1:3306/brikole_test?charset=utf8mb4"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    from app.models import Base

    eng = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with eng.connect():
            pass
    except SQLAlchemyError as exc:
        pytest.skip(f"no test database at {TEST_DATABASE_URL}: {exc.__class__.__name__}")

    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose work is undone when the test ends.

    `join_transaction_mode="create_savepoint"` turns the service layer's own
    commits into savepoint releases, so code under test can commit normally and
    the outer rollback still wipes the slate.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session):
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api_prefix() -> str:
    from app.main import API_PREFIX

    return API_PREFIX
