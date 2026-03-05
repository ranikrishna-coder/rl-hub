"""
HR & Payroll Workflow RL Environment
Workday, SAP SuccessFactors, ADP workflows. Definitions in apps/workflow_definitions/hr_payroll_workflows.json.
"""

import json
import os
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional

import sys
_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from environments.base_environment import (
    HealthcareRLEnvironment,
    RewardComponent,
    KPIMetrics,
)


def _load_workflow_definition() -> Dict[str, Any]:
    """Load HR Payroll workflow definition from apps folder."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "apps", "workflow_definitions", "hr_payroll_workflows.json")
    if not os.path.exists(path):
        return {"workflows": []}
    with open(path, "r") as f:
        return json.load(f)


class HRWorkflowEnv(HealthcareRLEnvironment):
    """
    Gymnasium-compatible RL environment for HR & Payroll workflows
    (Workday, SAP SuccessFactors, ADP) as defined in hr_payroll_workflows.json.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        **kwargs
    ):
        config = config or {}
        self._workflow_id = workflow_id or config.get("workflow_id", "workday_create_record")
        super().__init__(config=config, **kwargs)

        self._defn = _load_workflow_definition()
        workflows = self._defn.get("workflows", [])
        self._workflow = next(
            (w for w in workflows if w.get("id") == self._workflow_id),
            workflows[0] if workflows else {},
        )
        self._expected_order = self._workflow.get("expected_tool_order", ["build_payload", "validate", "submit"])
        self._min_required_calls = self._workflow.get("min_required_calls", len(self._expected_order))

        n_tools = len(self._expected_order)
        self.action_space = spaces.Discrete(n_tools + 1)
        state_dim = 2 + n_tools + 2
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(state_dim,), dtype=np.float32
        )

        self._step_index = 0
        self._tool_sequence: list = []
        self._valid_step_used = False
        self._workflow_complete = False

    def _get_state_features(self) -> np.ndarray:
        n = len(self._expected_order)
        step_norm = self._step_index / max(n, 1)
        done_flag = 1.0 if self._step_index >= self._min_required_calls else 0.0
        last_tool_onehot = np.zeros(n, dtype=np.float32)
        if self._tool_sequence:
            last_tool = self._tool_sequence[-1]
            for i, t in enumerate(self._expected_order):
                if t == last_tool:
                    last_tool_onehot[i] = 1.0
                    break
        valid = 1.0 if self._valid_step_used else 0.0
        complete = 1.0 if self._workflow_complete else 0.0
        return np.array(
            [step_norm, done_flag, *last_tool_onehot, valid, complete],
            dtype=np.float32,
        )

    def _initialize_state(self) -> np.ndarray:
        self._step_index = 0
        self._tool_sequence = []
        self._valid_step_used = False
        self._workflow_complete = False
        return self._get_state_features()

    def _apply_action(self, action: Any) -> Dict[str, Any]:
        n = len(self._expected_order)
        action = int(action)
        correct_next = self._step_index < n
        transition_info: Dict[str, Any] = {
            "action": action,
            "step_index": self._step_index,
            "correct_next_step": self._expected_order[self._step_index] if correct_next else None,
            "tool_sequence_before": list(self._tool_sequence),
        }

        if action == 0 and correct_next:
            tool = self._expected_order[self._step_index]
            self._tool_sequence.append(tool)
            self._step_index += 1
            self._valid_step_used = True
            if self._step_index >= self._min_required_calls:
                self._workflow_complete = True
            transition_info["tool_used"] = tool
            transition_info["valid_step"] = True
        else:
            if action > 0 and action <= n:
                wrong_tool = self._expected_order[action - 1]
                self._tool_sequence.append(wrong_tool)
            transition_info["tool_used"] = None
            transition_info["valid_step"] = False

        transition_info["tool_sequence_after"] = list(self._tool_sequence)
        transition_info["workflow_id"] = self._workflow_id
        return transition_info

    def _calculate_reward_components(
        self, state: np.ndarray, action: Any, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        comp = {
            RewardComponent.CLINICAL: 0.0,
            RewardComponent.FINANCIAL: 0.0,
            RewardComponent.PATIENT_SATISFACTION: 0.0,
            RewardComponent.RISK_PENALTY: 0.0,
        }
        if info.get("valid_step"):
            comp[RewardComponent.EFFICIENCY] = 0.5
            comp[RewardComponent.COMPLIANCE_PENALTY] = 0.0
        else:
            comp[RewardComponent.EFFICIENCY] = 0.0
            comp[RewardComponent.COMPLIANCE_PENALTY] = 0.5
        return comp

    def _is_done(self) -> bool:
        return self._step_index >= self._min_required_calls

    def _get_kpis(self) -> KPIMetrics:
        n = len(self._expected_order)
        steps_done = min(self._step_index, n)
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={
                "workflow_step": self._step_index,
                "expected_steps": n,
                "steps_completed": steps_done,
            },
            financial_metrics={},
            patient_satisfaction=0.0,
            risk_score=0.0,
            compliance_score=1.0 if self._step_index >= self._min_required_calls else 0.5,
            timestamp=float(self.time_step),
        )


# Workday
class WorkdayCreateRecordEnv(HRWorkflowEnv):
    """Workday: Create worker record with supervisory org and compensation."""
    ACTIONS = ["get_supervisory_org", "build_worker_payload", "post_worker"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="workday_create_record", **kwargs)


class WorkdayBulkImportEnv(HRWorkflowEnv):
    """Workday: Bulk integration with EIB processing and error summary."""
    ACTIONS = ["build_bulk_csv", "validate_rows", "launch_integration"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="workday_bulk_import", **kwargs)


class WorkdayTimeOffExpenseEnv(HRWorkflowEnv):
    """Workday: Time-off and expense report approval with balance validation."""
    ACTIONS = ["get_report", "validate_balance", "approve_request"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="workday_time_off_expense", **kwargs)


# SAP SuccessFactors
class SAPSuccessFactorsCreateRecordEnv(HRWorkflowEnv):
    """SAP SuccessFactors: Create employment record with job classification and pay group."""
    ACTIONS = ["get_job_classification", "build_employment_payload", "post_employment"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="sap_create_record", **kwargs)


class SAPSuccessFactorsBulkImportEnv(HRWorkflowEnv):
    """SAP SuccessFactors: Bulk upsert with validation and merge/insert report."""
    ACTIONS = ["build_bulk_payload", "validate_records", "post_upsert"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="sap_bulk_import", **kwargs)


class SAPSuccessFactorsOnboardingEnv(HRWorkflowEnv):
    """SAP SuccessFactors: Employee onboarding with forms and hiring manager tasks."""
    ACTIONS = ["get_onboarding_template", "assign_checklist", "launch_process"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="sap_onboarding", **kwargs)


# ADP
class ADPCreateWorkerEnv(HRWorkflowEnv):
    """ADP: Create worker with pay group, tax jurisdiction, and org assignment."""
    ACTIONS = ["get_pay_group", "build_worker_payload", "post_worker"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="adp_create_worker", **kwargs)


class ADPBulkImportEnv(HRWorkflowEnv):
    """ADP: Bulk worker import with position and pay calendar validation."""
    ACTIONS = ["validate_positions", "build_bulk_payload", "post_bulk"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="adp_bulk_import", **kwargs)


class ADPTimeOffPayrollEnv(HRWorkflowEnv):
    """ADP: Time-off request with accrual verification and approval workflow."""
    ACTIONS = ["get_accrual_balance", "validate_request", "submit_time_off"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="adp_time_off_payroll", **kwargs)
