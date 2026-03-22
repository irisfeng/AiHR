import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aihr.services import mineru_api


class FakeResponse:
    def __init__(self, status=200, body=""):
        self.status = status
        self._body = body.encode("utf-8")

    def read(self):
        return self._body


class FakeConnection:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def request(self, method, path, body=None, headers=None):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "body": body,
                "headers": headers or {},
            }
        )

    def getresponse(self):
        return FakeResponse(status=200, body="")

    def close(self):
        return None


class MinerUApiTests(unittest.TestCase):
    @patch("aihr.services.mineru_api.http.client.HTTPSConnection", return_value=FakeConnection())
    def test_upload_file_avoids_default_content_type_header(self, mock_connection):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "resume.pdf"
            file_path.write_bytes(b"fake-pdf")

            mineru_api._upload_file("https://example.com/upload?signature=demo", file_path)

        connection = mock_connection.return_value
        self.assertEqual(len(connection.calls), 1)
        call = connection.calls[0]
        self.assertEqual(call["method"], "PUT")
        self.assertEqual(call["path"], "/upload?signature=demo")
        self.assertIn("Content-Length", call["headers"])
        self.assertNotIn("Content-Type", call["headers"])


if __name__ == "__main__":
    unittest.main()
