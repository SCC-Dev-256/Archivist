from unittest.mock import MagicMock
from types import SimpleNamespace

magic = MagicMock()
from_file = MagicMock(return_value=SimpleNamespace(mime_type='application/octet-stream'))

