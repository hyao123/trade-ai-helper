"""
utils/ai_agent.py
-----------------
Autonomous AI Agent for end-to-end workflow automation.

The agent can execute multi-step tasks by planning, reasoning, and
calling internal tools sequentially. This is the "autopilot" mode
that differentiates from simple single-prompt generation.

Capabilities:
  - Plan a multi-step workflow from a high-level goal
  - Execute each step using internal tools (email, CRM, quotation, etc.)
  - Maintain context across steps
  - Handle errors and retry with alternative approaches
  - Report progress and ask for confirmation on critical actions

Example workflows:
  1. "Research company ABC and send them a cold email about LED lamps"
     → customer_profile → generate_email → review → send

  2. "Follow up with all customers who haven't replied in 7 days"
     → query_workflows → filter_due → batch_generate_followups → confirm → send

  3. "Prepare a quotation for 1000 units of product X to Brazil"
     → hs_lookup → tariff_calc → smart_quote → generate_pdf → save

Architecture:
  - AgentTask: represents a single action in the plan
  - AgentPlan: ordered list of tasks with dependencies
  - AgentExecutor: runs the plan step-by-step
  - Tools: wrappers around existing utils/* functions

Usage:
    from utils.ai_agent import Agent, run_agent

    agent = Agent(user_id="john")
    result = agent.run("Send a follow-up to all overdue customers")
    # result contains: plan, execution_log, outputs, status
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generator

from utils.logger import get_logger

logger = get_logger("ai_agent")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass
class AgentTask:
    """A single step in the agent's execution plan."""
    id: str
    name: str
    description: str
    tool: str  # Tool function to call
    params: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    requires_confirmation: bool = False
    depends_on: list[str] = field(default_factory=list)


@dataclass
class AgentPlan:
    """An ordered execution plan with tasks and metadata."""
    goal: str
    tasks: list[AgentTask] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    total_tokens_used: int = 0


@dataclass
class AgentResult:
    """Final result of an agent execution."""
    success: bool
    plan: AgentPlan
    outputs: dict = field(default_factory=dict)
    summary: str = ""
    execution_time_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Available tools (wrappers around existing functionality)
# ---------------------------------------------------------------------------

AGENT_TOOLS: dict[str, dict] = {
    "generate_cold_email": {
        "description": "Generate a personalized cold email for a prospect",
        "params": ["product", "customer", "features", "tone", "language"],
        "module": "utils.ai_client",
        "function": "generate_email",
    },
    "generate_followup": {
        "description": "Generate a follow-up email for an existing contact",
        "params": ["customer", "stage", "product"],
        "module": "utils.ai_client",
        "function": "generate_followup",
    },
    "generate_inquiry_reply": {
        "description": "Generate a reply to a customer inquiry",
        "params": ["inquiry", "customer_name", "your_name", "company_name"],
        "module": "utils.ai_client",
        "function": "reply_inquiry",
    },
    "generate_smart_quote": {
        "description": "Generate AI-powered pricing strategy and quotation",
        "params": ["product", "target_market", "order_quantity", "production_cost", "trade_term"],
        "module": "utils.ai_client",
        "function": "generate_smart_quote",
    },
    "lookup_hs_code": {
        "description": "Look up HS code for a product",
        "params": ["product", "description", "target_country"],
        "module": "utils.ai_client",
        "function": "lookup_hs_code",
    },
    "analyze_customer": {
        "description": "AI-powered customer profile analysis",
        "params": ["company_name", "website", "industry"],
        "module": "utils.ai_client",
        "function": "analyze_customer_profile",
    },
    "classify_email_intent": {
        "description": "Classify the intent of a customer email",
        "params": ["email_content", "context"],
        "module": "utils.ai_client",
        "function": "recognize_email_intent",
    },
    "send_email": {
        "description": "Send an email to a customer (requires confirmation)",
        "params": ["to_email", "subject", "body"],
        "module": "utils.email_service",
        "function": "send_ai_generated_email",
        "requires_confirmation": True,
    },
    "add_customer": {
        "description": "Add a customer to the CRM",
        "params": ["company", "contact", "email", "country", "product", "stage"],
        "module": "utils.customers",
        "function": "add_customer",
    },
    "get_due_followups": {
        "description": "Get list of customers due for follow-up",
        "params": [],
        "module": "utils.workflow",
        "function": "get_due_workflows",
    },
    "calculate_duty": {
        "description": "Calculate import duty and landed cost",
        "params": ["hs_code", "cif_value_usd", "destination_country"],
        "module": "utils.customs_data",
        "function": "calculate_duty",
    },
    "score_customer": {
        "description": "Compute behavior score for a customer",
        "params": ["customer"],
        "module": "utils.customer_scoring",
        "function": "compute_behavior_score",
    },
}


# ---------------------------------------------------------------------------
# Planning prompt
# ---------------------------------------------------------------------------

_PLANNING_SYSTEM = """You are an AI trade assistant agent that plans and executes multi-step workflows.

Given a user's goal, create an execution plan using available tools.
Each step should be a specific tool call with clear parameters.

Available tools:
{tools_description}

Rules:
1. Break complex goals into sequential steps
2. Each step must use exactly one tool from the list
3. Steps can reference outputs from previous steps
4. Mark steps that modify external state (send_email, add_customer) as requires_confirmation=true
5. Keep plans concise (2-6 steps for most tasks)
6. Output ONLY valid JSON (no markdown, no explanation)

Output format:
{{"tasks": [
  {{"id": "1", "name": "step name", "tool": "tool_name", "params": {{"key": "value"}}, "requires_confirmation": false, "depends_on": []}},
  {{"id": "2", "name": "step name", "tool": "tool_name", "params": {{"key": "value or {{1.output}}"}}, "requires_confirmation": true, "depends_on": ["1"]}}
]}}
"""

_PLANNING_PROMPT = """Goal: {goal}

Context:
- User: {user_id}
- Current time: {current_time}
- Additional context: {context}

Create an execution plan (JSON only):"""


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class Agent:
    """
    Autonomous AI Agent that plans and executes multi-step trade workflows.

    Example:
        agent = Agent(user_id="john")
        result = agent.run("Send follow-ups to all overdue customers")
    """

    def __init__(self, user_id: str = "default", context: str = ""):
        self.user_id = user_id
        self.context = context
        self._plan: AgentPlan | None = None
        self._execution_log: list[dict] = []

    def plan(self, goal: str) -> AgentPlan:
        """
        Create an execution plan for a goal (without executing it).

        Args:
            goal: Natural language description of what to accomplish

        Returns:
            AgentPlan with ordered tasks
        """
        from utils.ai_client import call_llm

        # Build tools description for the planning prompt
        tools_desc = "\n".join(
            f"- {name}: {info['description']} (params: {', '.join(info['params'])})"
            for name, info in AGENT_TOOLS.items()
        )

        system = _PLANNING_SYSTEM.format(tools_description=tools_desc)
        prompt = _PLANNING_PROMPT.format(
            goal=goal,
            user_id=self.user_id,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            context=self.context or "No additional context",
        )

        # Get plan from AI
        response = call_llm(prompt, system, user_id=self.user_id, temperature=0.2)

        # Parse the plan
        plan = self._parse_plan(goal, response)
        self._plan = plan

        logger.info("Agent plan created: %d tasks for goal='%s'", len(plan.tasks), goal[:50])
        return plan

    def run(self, goal: str, auto_confirm: bool = False) -> AgentResult:
        """
        Plan and execute a workflow end-to-end.

        Args:
            goal: What to accomplish
            auto_confirm: If True, skip confirmation prompts (dangerous!)

        Returns:
            AgentResult with plan, outputs, and summary
        """
        start_time = time.time()

        # Phase 1: Planning
        plan = self.plan(goal)
        if not plan.tasks:
            return AgentResult(
                success=False,
                plan=plan,
                summary="Failed to create a valid execution plan",
            )

        # Phase 2: Execution
        outputs: dict[str, Any] = {}

        for task in plan.tasks:
            # Check dependencies
            deps_met = all(
                plan.tasks[int(dep_id) - 1].status == TaskStatus.COMPLETED
                for dep_id in task.depends_on
                if dep_id.isdigit() and int(dep_id) - 1 < len(plan.tasks)
            )
            if not deps_met:
                task.status = TaskStatus.SKIPPED
                task.error = "Dependencies not met"
                continue

            # Check if confirmation needed
            if task.requires_confirmation and not auto_confirm:
                task.status = TaskStatus.NEEDS_CONFIRMATION
                self._log("confirmation_needed", task)
                continue

            # Execute the task
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._log("task_started", task)

            try:
                result = self._execute_task(task, outputs)
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                outputs[task.id] = result
                self._log("task_completed", task)
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()
                self._log("task_failed", task, error=str(e))
                logger.warning("Agent task failed: %s — %s", task.name, e)

        # Phase 3: Summary
        plan.status = self._determine_plan_status(plan)
        plan.completed_at = datetime.now().isoformat()

        elapsed = time.time() - start_time
        summary = self._generate_summary(plan, outputs)

        return AgentResult(
            success=plan.status == TaskStatus.COMPLETED,
            plan=plan,
            outputs=outputs,
            summary=summary,
            execution_time_seconds=round(elapsed, 2),
        )

    def run_stream(self, goal: str) -> Generator[dict, None, AgentResult]:
        """
        Stream execution progress as it happens.

        Yields progress dicts, returns final AgentResult.

        Usage:
            gen = agent.run_stream("Send follow-ups")
            for progress in gen:
                display(progress)  # {"step": 1, "status": "running", "message": "..."}
            result = gen.value  # Final result after StopIteration
        """
        start_time = time.time()
        plan = self.plan(goal)

        yield {"type": "plan_created", "tasks": len(plan.tasks), "goal": goal}

        if not plan.tasks:
            return AgentResult(success=False, plan=plan, summary="No plan created")

        outputs: dict[str, Any] = {}

        for i, task in enumerate(plan.tasks):
            yield {
                "type": "task_started",
                "step": i + 1,
                "total": len(plan.tasks),
                "name": task.name,
                "tool": task.tool,
            }

            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()

            try:
                result = self._execute_task(task, outputs)
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                outputs[task.id] = result

                yield {
                    "type": "task_completed",
                    "step": i + 1,
                    "name": task.name,
                    "result_preview": str(result)[:200] if result else "",
                }
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                yield {"type": "task_failed", "step": i + 1, "name": task.name, "error": str(e)}

        plan.status = self._determine_plan_status(plan)
        elapsed = time.time() - start_time

        return AgentResult(
            success=plan.status == TaskStatus.COMPLETED,
            plan=plan,
            outputs=outputs,
            summary=self._generate_summary(plan, outputs),
            execution_time_seconds=round(elapsed, 2),
        )

    # ── Execution engine ──────────────────────────────

    def _execute_task(self, task: AgentTask, previous_outputs: dict) -> Any:
        """Execute a single task by calling the appropriate tool function."""
        tool_config = AGENT_TOOLS.get(task.tool)
        if not tool_config:
            raise ValueError(f"Unknown tool: {task.tool}")

        # Resolve parameter references to previous outputs
        resolved_params = self._resolve_params(task.params, previous_outputs)

        # Dynamic import and call
        module_path = tool_config["module"]
        function_name = tool_config["function"]

        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)

        # Call the function
        # Handle different parameter styles
        if not resolved_params:
            result = func()
        elif isinstance(resolved_params, dict):
            # Add user_id if the function accepts it
            import inspect
            sig = inspect.signature(func)
            if "user_id" in sig.parameters and "user_id" not in resolved_params:
                resolved_params["user_id"] = self.user_id
            if "stream" in sig.parameters and "stream" not in resolved_params:
                resolved_params["stream"] = False
            result = func(**resolved_params)
        else:
            result = func(resolved_params)

        return result

    def _resolve_params(self, params: dict, outputs: dict) -> dict:
        """
        Resolve parameter values that reference previous step outputs.

        Syntax: {step_id.output} or {step_id.output.key}
        Example: {"customer": "{1.output}"} → uses output from step 1
        """
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                ref = value[1:-1]  # Strip braces
                parts = ref.split(".")
                if len(parts) >= 2 and parts[0] in outputs:
                    output = outputs[parts[0]]
                    # Navigate nested keys
                    for part in parts[1:]:
                        if part == "output":
                            continue
                        if isinstance(output, dict):
                            output = output.get(part, output)
                    resolved[key] = output
                else:
                    resolved[key] = value
            else:
                resolved[key] = value
        return resolved

    # ── Plan parsing ──────────────────────────────────

    def _parse_plan(self, goal: str, ai_response: str) -> AgentPlan:
        """Parse AI-generated plan JSON into AgentPlan.

        Returns a plan with no tasks when the LLM returned a user-facing error
        string (``call_llm`` uses a ``⚠️`` prefix for rate-limit/key/provider
        failures) or unparseable JSON, so callers report a failure instead of
        silently fabricating an unrelated tool invocation.
        """
        plan = AgentPlan(goal=goal)

        # A ⚠️-prefixed response is a user-facing error from call_llm (rate limit,
        # missing key, provider failure) — never a valid plan. Do not turn it into
        # a hard-coded tool call that executes the wrong action.
        if ai_response.lstrip().startswith("⚠️"):
            logger.warning("Agent plan rejected: LLM returned an error (goal='%s')", goal[:60])
            return plan  # no tasks -> callers report a failed plan

        # Clean response (handle markdown wrapping) and parse JSON in one step.
        from utils.sanitize import parse_llm_json
        data = parse_llm_json(ai_response)

        if data is None:
            logger.warning("Failed to parse agent plan (response: %s)", str(ai_response)[:200])
            # Return an empty-task plan so the agent reports a failure instead of
            # silently invoking a guessed tool with the raw goal as a parameter.
            return plan

        tasks_data = data.get("tasks", [])
        for td in tasks_data:
            tool_name = td.get("tool", "")
            if tool_name not in AGENT_TOOLS:
                continue  # Skip unknown tools

            task = AgentTask(
                id=str(td.get("id", len(plan.tasks) + 1)),
                name=td.get("name", f"Step {len(plan.tasks) + 1}"),
                description=td.get("description", ""),
                tool=tool_name,
                params=td.get("params", {}),
                requires_confirmation=td.get(
                    "requires_confirmation",
                    AGENT_TOOLS[tool_name].get("requires_confirmation", False),
                ),
                depends_on=td.get("depends_on", []),
            )
            plan.tasks.append(task)

        return plan

    # ── Helpers ───────────────────────────────────────

    def _determine_plan_status(self, plan: AgentPlan) -> TaskStatus:
        """Determine overall plan status from individual task statuses."""
        statuses = [t.status for t in plan.tasks]
        if all(s == TaskStatus.COMPLETED for s in statuses):
            return TaskStatus.COMPLETED
        if any(s == TaskStatus.FAILED for s in statuses):
            return TaskStatus.FAILED
        if any(s == TaskStatus.NEEDS_CONFIRMATION for s in statuses):
            return TaskStatus.NEEDS_CONFIRMATION
        if any(s == TaskStatus.RUNNING for s in statuses):
            return TaskStatus.RUNNING
        return TaskStatus.PENDING

    def _generate_summary(self, plan: AgentPlan, outputs: dict) -> str:
        """Generate a human-readable summary of the execution."""
        completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in plan.tasks if t.status == TaskStatus.FAILED)
        total = len(plan.tasks)

        lines = ["## Agent Execution Summary"]
        lines.append(f"**Goal:** {plan.goal}")
        lines.append(f"**Status:** {plan.status.value}")
        lines.append(f"**Progress:** {completed}/{total} steps completed")

        if failed > 0:
            lines.append(f"**Failures:** {failed} steps failed")

        lines.append("")
        lines.append("### Steps:")
        for task in plan.tasks:
            icon = {
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.SKIPPED: "⏭️",
                TaskStatus.NEEDS_CONFIRMATION: "⏸️",
                TaskStatus.PENDING: "⏳",
                TaskStatus.RUNNING: "🔄",
            }.get(task.status, "•")
            lines.append(f"{icon} {task.name} ({task.tool})")
            if task.error:
                lines.append(f"   Error: {task.error}")

        return "\n".join(lines)

    def _log(self, event: str, task: AgentTask, **extra) -> None:
        """Add entry to execution log."""
        self._execution_log.append({
            "event": event,
            "task_id": task.id,
            "task_name": task.name,
            "timestamp": datetime.now().isoformat(),
            **extra,
        })


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_agent(
    goal: str,
    user_id: str = "default",
    context: str = "",
    auto_confirm: bool = False,
) -> AgentResult:
    """
    Quick-start function to run an agent workflow.

    Args:
        goal: What to accomplish (natural language)
        user_id: User context for rate limiting and data access
        context: Additional context (e.g., "focus on LED products")
        auto_confirm: Skip confirmation prompts

    Returns:
        AgentResult with execution details

    Example:
        result = run_agent(
            "Generate a cold email for ABC Corp about our LED desk lamps",
            user_id="john",
        )
        if result.success:
            print(result.outputs)
    """
    agent = Agent(user_id=user_id, context=context)
    return agent.run(goal, auto_confirm=auto_confirm)


def get_available_tools() -> list[dict]:
    """Get list of tools the agent can use (for UI display)."""
    return [
        {
            "name": name,
            "description": info["description"],
            "params": info["params"],
            "requires_confirmation": info.get("requires_confirmation", False),
        }
        for name, info in AGENT_TOOLS.items()
    ]
