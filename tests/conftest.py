import os
import pytest
from app import create_app
from app.extensions import db as _db

TEST_DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://bank:bank@localhost:5432/testdb'
)


@pytest.fixture(scope='session')
def app():
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URL,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture(scope='session')
def db(app):
    return _db


@pytest.fixture(autouse=True)
def clean_db(db):
    yield
    db.session.rollback()
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()
