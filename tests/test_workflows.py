import unittest

from aihr.setup.access import AIHR_HIRING_MANAGER_ROLE, HR_MANAGER_ROLE
from aihr.setup.workflows import (
    JOB_REQUISITION_RUNTIME_STATUS_SYNC,
    JOB_REQUISITION_STATUS_TO_WORKFLOW_STATE,
    JOB_REQUISITION_WORKFLOW_NAME,
    JOB_REQUISITION_WORKFLOW_STATES,
    JOB_REQUISITION_WORKFLOW_TRANSITIONS,
)


class JobRequisitionWorkflowTests(unittest.TestCase):
    def test_workflow_name_is_stable(self):
        self.assertEqual(JOB_REQUISITION_WORKFLOW_NAME, "AIHR Job Requisition Approval")

    def test_workflow_covers_key_business_states(self):
        states = {row["state"] for row in JOB_REQUISITION_WORKFLOW_STATES}
        self.assertEqual(
            states,
            {"草稿", "待HR处理", "已批准", "已驳回", "已暂停", "已完成", "已取消"},
        )

    def test_manager_and_hr_transitions_exist(self):
        transitions = {
            (row["state"], row["action"], row["next_state"], row["allowed"])
            for row in JOB_REQUISITION_WORKFLOW_TRANSITIONS
        }
        self.assertIn(("草稿", "提交需求", "待HR处理", AIHR_HIRING_MANAGER_ROLE), transitions)
        self.assertIn(("待HR处理", "批准开启", "已批准", HR_MANAGER_ROLE), transitions)
        self.assertIn(("待HR处理", "退回修改", "已驳回", HR_MANAGER_ROLE), transitions)
        self.assertIn(("已驳回", "重新提交", "待HR处理", AIHR_HIRING_MANAGER_ROLE), transitions)

    def test_existing_status_mapping_is_defined(self):
        self.assertEqual(JOB_REQUISITION_STATUS_TO_WORKFLOW_STATE["Open & Approved"], "已批准")
        self.assertEqual(JOB_REQUISITION_STATUS_TO_WORKFLOW_STATE["Filled"], "已完成")

    def test_runtime_sync_only_applies_to_terminal_statuses(self):
        self.assertNotIn("Pending", JOB_REQUISITION_RUNTIME_STATUS_SYNC)
        self.assertEqual(JOB_REQUISITION_RUNTIME_STATUS_SYNC["Filled"], "已完成")
        self.assertEqual(JOB_REQUISITION_RUNTIME_STATUS_SYNC["Cancelled"], "已取消")


if __name__ == "__main__":
    unittest.main()
