import unittest

from aihr.setup.departments import AIHR_DEPARTMENT_NAMES, DEMO_HR_ACCOUNTS, DEMO_MANAGER_ACCOUNTS


class DepartmentSetupTests(unittest.TestCase):
    def test_aihr_uses_flat_primary_departments(self):
        self.assertEqual(
            AIHR_DEPARTMENT_NAMES,
            [
                "市场部",
                "销售部",
                "销售划小单元",
                "运营中心",
                "政务热线运营中心",
                "财务部",
                "人事部",
                "交付中心",
                "产研中心",
            ],
        )

    def test_demo_manager_accounts_cover_hr_and_delivery_centers(self):
        account_map = {item["user_id"]: item for item in DEMO_MANAGER_ACCOUNTS}
        self.assertEqual(account_map["manager.demo@aihr.local"]["department_name"], "人事部")
        self.assertEqual(account_map["delivery.manager@aihr.local"]["department_name"], "交付中心")
        self.assertEqual(account_map["delivery.manager@aihr.local"]["designation_name"], "交付中心经理")

    def test_demo_hr_account_is_not_department_scoped(self):
        account_map = {item["user_id"]: item for item in DEMO_HR_ACCOUNTS}
        self.assertEqual(account_map["hr.demo@aihr.local"]["department_name"], "人事部")
        self.assertFalse(account_map["hr.demo@aihr.local"]["scope_to_department"])


if __name__ == "__main__":
    unittest.main()
