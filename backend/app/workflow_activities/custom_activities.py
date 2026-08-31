"""
Custom & Extensible Workflow Activities Registry.

Enterprise developers can define domain tasks here or in dynamic modules.
Activities registered with @registry.register("Name") will automatically be adiscoverable
in Workflow Studio and executed by SpiffWorkflow Engine.
"""

from typing import Any, Dict
from app.workflow.runtime.base_activity import BaseActivity
from app.workflow.runtime.context import WorkflowContext
from app.workflow.runtime.registry import registry
from app.core.logger import logger

@registry.register("CustomCalculationActivity")
class CustomCalculationActivity(BaseActivity):
    """
    Sample custom service task for calculating dynamic variables.
    """
    def validate(self, context: WorkflowContext) -> bool:
        return True

    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        input_value = context.get_variable("amount") or 0
        tax_rate = context.get_variable("tax_rate") or 0.18
        calculated_total = float(input_value) * (1.0 + float(tax_rate))
        
        context.set_variable("total_amount", calculated_total)
        logger.info(f"[CustomCalculationActivity] Calculated total: {calculated_total}")
        return {"total_amount": calculated_total}

    def rollback(self, context: WorkflowContext) -> Dict[str, Any]:
        return {"compensated": True}
