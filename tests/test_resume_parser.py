import unittest

from aihr.services.resume_parser import infer_name_from_file_name, parse_resume_text


class ResumeParserTests(unittest.TestCase):
    def test_extracts_basic_fields(self):
        resume_text = """
        Jane Smith
        jane@demo.com
        +86 138-0013-8000
        Location: Shanghai
        6 years of experience in recruiting, onboarding, payroll, and excel.
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "Jane Smith")
        self.assertEqual(result["city"], "Shanghai")
        self.assertEqual(result["years_of_experience"], 6)
        self.assertIn("jane@demo.com", result["emails"])
        self.assertIn("recruiting", result["skills"])
        self.assertIn("excel", result["skills"])

    def test_extracts_chinese_resume_fields(self):
        resume_text = """
        张敏
        zhangmin@demo.com
        13800138001
        现居：上海
        5年招聘、入职、薪酬和员工关系经验，熟悉 Excel 与数据分析。
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "张敏")
        self.assertEqual(result["city"], "上海")
        self.assertEqual(result["years_of_experience"], 5)
        self.assertIn("招聘", result["skills"])
        self.assertIn("入职", result["skills"])
        self.assertIn("薪酬", result["skills"])
        self.assertIn("员工关系", result["skills"])

    def test_extracts_name_from_real_style_chinese_resume(self):
        resume_text = """
        姓 名 冯尽威 年 龄 24
        民 族 汉 学 历 大专
        工作经验 3 年 住 址 北京市朝阳区(可搬迁）
        邮 箱 15525740115@163.com 电 话 15525740115
        求职意向
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "冯尽威")
        self.assertEqual(result["years_of_experience"], 3)
        self.assertEqual(result["phones"], ["15525740115"])

    def test_skips_heading_like_lines_when_inferring_name(self):
        resume_text = """
        工作经历
        个人技能
        刘青云
        男 | 42岁 | lwy.wuyun@163.com
        22年工作经验 | 求职意向：设备维修保养工程师 | 期望城市：上海
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["name"], "刘青云")
        self.assertEqual(result["city"], "上海")
        self.assertEqual(result["years_of_experience"], 22)

    def test_ignores_date_like_numbers_in_phone_candidates(self):
        resume_text = """
        戚晨翔
        18101645061
        2008-2011 某公司
        2012-2018 某公司
        332889084@qq.com
        """

        result = parse_resume_text(resume_text)

        self.assertEqual(result["phones"], ["18101645061"])

    def test_infers_name_from_real_chinese_file_names(self):
        self.assertEqual(infer_name_from_file_name("买鑫实施运维工程师.pdf"), "买鑫")
        self.assertEqual(infer_name_from_file_name("冯尽威运维工程师.pdf"), "冯尽威")
        self.assertEqual(infer_name_from_file_name("刘青云简历-15921122089.pdf"), "刘青云")
        self.assertEqual(infer_name_from_file_name("李天耀-项目经理&实施顾问.pdf"), "李天耀")

    def test_detects_delivery_and_ops_skill_keywords(self):
        resume_text = """
        买鑫
        15710031625
        5年运维经验
        熟悉 Linux、Docker、K8S、Nginx、MySQL、Redis、Ansible、Shell。
        负责实施交付、监控告警、容器化部署与技术支持。
        """

        result = parse_resume_text(resume_text)

        for skill in ["linux", "docker", "k8s", "nginx", "mysql", "redis", "ansible", "shell", "实施", "交付", "运维", "监控", "技术支持"]:
            self.assertIn(skill, result["skills"])


if __name__ == "__main__":
    unittest.main()
