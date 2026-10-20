"""
Tests against a real Postgres, for what only the database can tell: its
rules (one status per point, no repeated tags) and the queries of the stores.

They need CHATMAP_TEST_DATABASE_URL, a Postgres with PostGIS where the user
can create databases, for example:

    CHATMAP_TEST_DATABASE_URL=postgresql://admin:<password>@localhost:5432/postgres

A database is made for the run, every migration applied to it, and dropped at
the end. Without the variable these tests are skipped.
"""
import os
import uuid
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import db as chatmap_db

TEST_DATABASE_URL = os.getenv("CHATMAP_TEST_DATABASE_URL")
API_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The tables the tests write in, emptied after each one
TABLES = ["point_tag_changes", "point_tags", "map_key_values", "map_keys", "points", "maps"]


def _migrate(url):
    # alembic/env.py builds its url from these, without a port
    environment = {
        "CHATMAP_DB_HOST": f"{url.host}:{url.port or 5432}",
        "CHATMAP_DB_USER": url.username,
        "CHATMAP_DB_PASSWORD": url.password,
        "CHATMAP_DB": url.database,
    }
    with patch.dict(os.environ, environment):
        command.upgrade(Config(toml_file=os.path.join(API_DIR, "pyproject.toml")), "head")


@pytest.fixture(scope="session")
def pg_engine():
    if not TEST_DATABASE_URL:
        pytest.skip("CHATMAP_TEST_DATABASE_URL is not set")

    server = make_url(TEST_DATABASE_URL)
    name = f"chatmap_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(server, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))

    url = server.set(database=name)
    try:
        # Points have a geometry
        postgis = create_engine(url, isolation_level="AUTOCOMMIT")
        with postgis.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        postgis.dispose()

        _migrate(url)
        engine = create_engine(url)
        yield engine
        engine.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def pg(pg_engine):
    """The stores write in the test database; it is emptied after each test."""
    test_sessions = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)
    with patch.object(chatmap_db, "SessionLocal", test_sessions):
        yield test_sessions
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} CASCADE"))
