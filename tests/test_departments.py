import unittest

from aihr.setup.departments import AIHR_DEPARTMENT_NAMES


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


if __name__ == "__main__":
    unittest.main()
