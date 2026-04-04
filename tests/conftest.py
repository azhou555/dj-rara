import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_sp():
    sp = MagicMock()
    sp.current_user.return_value = {"id": "testuser", "display_name": "Test User"}
    return sp
