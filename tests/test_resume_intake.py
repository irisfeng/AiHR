import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from aihr.services.resume_intake import extract_resume_archive, summarize_archive_results
from aihr.services.resume_parser import extract_text_from_file


DOCX_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>张三</w:t></w:r></w:p>
    <w:p><w:r><w:t>现居上海</w:t></w:r></w:p>
    <w:p><w:r><w:t>5年招聘经验，熟悉招聘、面试、入职。</w:t></w:r></w:p>
    <w:p><w:r><w:t>zhangsan@example.com</w:t></w:r></w:p>
  </w:body>
</w:document>
"""


class ResumeIntakeTests(unittest.TestCase):
    def test_extracts_text_from_docx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "resume.docx"
            with ZipFile(docx_path, "w") as archive:
                archive.writestr("[Content_Types].xml", "")
                archive.writestr("word/document.xml", DOCX_XML)

            text = extract_text_from_file(docx_path)
            self.assertIn("张三", text)
            self.assertIn("zhangsan@example.com", text)

    def test_extracts_supported_files_from_zip_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "bundle.zip"
            with ZipFile(archive_path, "w") as bundle:
                bundle.writestr("candidates/resume.docx", self._build_docx_bytes())
                bundle.writestr("resume.txt", "李四\n现居杭州\n3年招聘运营经验\nlisi@example.com")
                bundle.writestr("notes.xlsx", b"binary")

            items = extract_resume_archive(archive_path)
            summary = summarize_archive_results(items)

            self.assertEqual(summary["total_files"], 3)
            self.assertEqual(summary["parsed_count"], 2)
            self.assertEqual(summary["unsupported_count"], 1)
            parsed_names = [item["parsed_resume"].get("name") for item in items if item["status"] == "Parsed"]
            self.assertIn("张三", parsed_names)
            self.assertIn("李四", parsed_names)

    @staticmethod
    def _build_docx_bytes() -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "resume.docx"
            with ZipFile(docx_path, "w") as archive:
                archive.writestr("[Content_Types].xml", "")
                archive.writestr("word/document.xml", DOCX_XML)
            return docx_path.read_bytes()


if __name__ == "__main__":
    unittest.main()
