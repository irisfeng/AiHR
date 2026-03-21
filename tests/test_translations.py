import csv
import unittest
from pathlib import Path


TRANSLATION_FILE = Path(__file__).resolve().parents[1] / "aihr" / "translations" / "zh.csv"


def load_translations() -> dict[str, str]:
    with TRANSLATION_FILE.open(newline="", encoding="utf-8") as handle:
        rows = csv.reader(handle)
        return {row[0]: row[1] for row in rows if len(row) >= 2 and row[0] and row[1]}


class TranslationCoverageTests(unittest.TestCase):
    def test_recruitment_core_pages_have_chinese_labels(self):
        translations = load_translations()
        expected = {
            "Job Requisition": "岗位需求单",
            "New Job Requisition": "新建岗位需求单",
            "Add Job Requisition": "新增岗位需求单",
            "AI Screening": "AI 初筛",
            "New AI Screening": "新建 AI 初筛",
            "Add AI Screening": "新增 AI 初筛",
            "Job Opening": "招聘中岗位",
            "Job Applicant": "候选人档案",
            "Interview": "面试安排",
            "Interview Feedback": "面试反馈",
            "Job Offer": "Offer 管理",
            "Employee Onboarding": "入职交接",
            "HR": "人力资源",
        }
        for source, target in expected.items():
            self.assertEqual(translations.get(source), target)

    def test_common_list_and_form_labels_have_chinese_overrides(self):
        translations = load_translations()
        expected = {
            "List View": "列表视图",
            "Filter By": "过滤条件",
            "Assigned To": "已分配给",
            "Created By": "创建人",
            "Last Updated On": "最后更新时间",
            "Naming Series": "编号规则",
            "Timelines": "时间安排",
            "Posting Date": "发布日期",
            "Expected Compensation": "预期薪酬",
            "Requested By": "需求提出人",
            "No. of Positions": "招聘人数",
            "No of. Positions": "招聘人数",
            "Expected By": "期望到岗日期",
            "Clear all filters": "清空全部过滤条件",
            "Begin typing for results.": "开始输入以查看结果。",
        }
        for source, target in expected.items():
            self.assertEqual(translations.get(source), target)


if __name__ == "__main__":
    unittest.main()
