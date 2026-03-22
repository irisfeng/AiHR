import tempfile
import unittest
from unittest.mock import patch
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

    def test_preserves_chinese_file_names_and_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "中文简历包.zip"
            with ZipFile(archive_path, "w") as bundle:
                bundle.writestr(
                    "王小雨_招聘经理.docx",
                    self._build_custom_docx_bytes(
                        [
                            "王小雨",
                            "wangxiaoyu@demo.com",
                            "13800138011",
                            "现居：上海",
                            "6年招聘、面试、入职和数据分析经验。",
                        ]
                    ),
                )
                bundle.writestr(
                    "李娜_招聘运营.txt",
                    "\n".join(
                        [
                            "李娜",
                            "lina@demo.com",
                            "13800138012",
                            "现居：杭州",
                            "4年招聘运营、面试协调、入职办理经验，熟悉招聘、面试、入职、沟通。",
                        ]
                    ),
                )
                bundle.writestr("供应商说明.xlsx", b"binary")

            items = extract_resume_archive(archive_path)
            parsed_items = {item["file_name"]: item for item in items if item["status"] == "Parsed"}
            unsupported_items = [item for item in items if item["status"] == "Unsupported"]

            self.assertIn("王小雨_招聘经理.docx", parsed_items)
            self.assertIn("李娜_招聘运营.txt", parsed_items)
            self.assertEqual(parsed_items["王小雨_招聘经理.docx"]["parsed_resume"]["name"], "王小雨")
            self.assertEqual(parsed_items["王小雨_招聘经理.docx"]["parsed_resume"]["city"], "上海")
            self.assertEqual(parsed_items["王小雨_招聘经理.docx"]["parsed_resume"]["years_of_experience"], 6)
            self.assertEqual(parsed_items["李娜_招聘运营.txt"]["parsed_resume"]["name"], "李娜")
            self.assertEqual(parsed_items["李娜_招聘运营.txt"]["parsed_resume"]["city"], "杭州")
            self.assertEqual(parsed_items["李娜_招聘运营.txt"]["parsed_resume"]["years_of_experience"], 4)
            self.assertEqual(len(unsupported_items), 1)
            self.assertEqual(unsupported_items[0]["file_name"], "供应商说明.xlsx")

    @patch("aihr.services.resume_intake.extract_pdf_texts_with_mineru")
    @patch("aihr.services.resume_intake.mineru_is_enabled", return_value=True)
    def test_uses_mineru_for_pdf_files_in_zip_bundle(self, _enabled, mock_batch_extract):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "pdf_bundle.zip"
            with ZipFile(archive_path, "w") as bundle:
                bundle.writestr("张三_运维工程师.pdf", b"%PDF-1.4 fake")

            mock_batch_extract.side_effect = lambda file_paths: {
                str(file_paths[0]): type(
                    "MinerUParsedFile",
                    (),
                    {"text": "张三\n13800138022\n现居：上海\n6年运维经验\n熟悉 Linux、Docker、K8S。"},
                )()
            }

            items = extract_resume_archive(archive_path)
            parsed_items = [item for item in items if item["status"] == "Parsed"]

            self.assertEqual(len(parsed_items), 1)
            self.assertEqual(parsed_items[0]["parser_engine"], "MinerU API")
            self.assertEqual(parsed_items[0]["parsed_resume"]["name"], "张三")
            self.assertIn("linux", parsed_items[0]["parsed_resume"]["skills"])

    @staticmethod
    def _build_docx_bytes() -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "resume.docx"
            with ZipFile(docx_path, "w") as archive:
                archive.writestr("[Content_Types].xml", "")
                archive.writestr("word/document.xml", DOCX_XML)
            return docx_path.read_bytes()

    @staticmethod
    def _build_custom_docx_bytes(paragraphs: list[str]) -> bytes:
        xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            "  <w:body>",
        ]
        for paragraph in paragraphs:
            content = (
                paragraph.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            xml.append(f"    <w:p><w:r><w:t>{content}</w:t></w:r></w:p>")
        xml += ["  </w:body>", "</w:document>"]

        with tempfile.TemporaryDirectory() as temp_dir:
            docx_path = Path(temp_dir) / "resume.docx"
            with ZipFile(docx_path, "w") as archive:
                archive.writestr("[Content_Types].xml", "")
                archive.writestr("word/document.xml", "\n".join(xml))
            return docx_path.read_bytes()


if __name__ == "__main__":
    unittest.main()
