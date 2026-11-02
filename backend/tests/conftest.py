import os
import shutil
import sys
import tempfile
from pathlib import Path

# Ensure the backend root directory is in sys.path for test execution
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

test_data_dir = Path(tempfile.mkdtemp(prefix="reloop-tests-"))
test_database_path = test_data_dir / "test.db"
os.environ["APP_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-only-signing-key-not-for-production-123456"
os.environ["DATABASE_URL"] = f"sqlite:///{test_database_path.as_posix()}"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@test.reloop"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "test-only-admin-password"

from app.database import Base, engine
from app.seeds.seed_data import seed_database

import app.models

import pytest

@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield
    engine.dispose()
    shutil.rmtree(test_data_dir, ignore_errors=True)
