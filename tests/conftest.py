"""
Shared pytest fixtures.
The inventory list is reset before every test so tests don't affect each other.
"""

import copy

import pytest

import data
from app import app as flask_app

ORIGINAL_INVENTORY = copy.deepcopy(data.inventory)


@pytest.fixture(autouse=True)
def reset_inventory():
    """Restore the mock database before each test (same list object, fresh contents)."""
    data.inventory.clear()
    data.inventory.extend(copy.deepcopy(ORIGINAL_INVENTORY))
    yield


@pytest.fixture
def client():
    """Flask test client for calling routes without running the server."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client