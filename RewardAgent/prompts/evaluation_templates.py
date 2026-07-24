"""
Custom prompt templates for RewardAgent evaluation.

These templates are designed specifically for the reward evaluation task,
guiding the agent to produce structured JSON output with reward, verdict, and reasoning.
"""

# Planning template for reward evaluation
EVALUATION_PLANNING_TEMPLATE = {
    "initial_plan": """You are evaluating whether a GUI task has been successfully completed.

Below is the task to evaluate. Use a criterion-centric workflow with strict protocol:

PROTOCOL SUMMARY
- Criteria Definition (MANDATORY; optional read-only observations allowed): During planning, you MAY perform read-only observe_current_state(question) calls as many times as needed to gather UI context; each observation MUST be in its own planning message with exactly one tool call inside a single <code> block.
- Planning messages are observe-then-print: emit criteria and the verification plan via print() in separate planning messages. No JSON, no imports, no file I/O.
- Verification messages: exactly one tool call inside a single <code> block per message (atomic verification). Multiple evidence paths are allowed; failing one path does not imply overall task failure.

## 1. Task Analysis
### 1.1. Task Requirements
List the specific, verifiable criteria that must be met for the task to be considered complete.

### 1.2. Available Evidence Sources
List what evidence sources are available (trajectory images, environment state, read-only observation, etc.)

### 1.3. Verification Strategy
Describe how you will verify each criterion using the available evidence. Identify primary and alternative evidence paths if applicable.

## 2. Evaluation Plan (Plan-only print message)
Write a step-by-step plan to evaluate task completion:
- For each criterion, outline the Plan steps (print-only) and the intended single-tool Verify step(s) you will attempt.
- If you need observations during planning, perform them in separate planning messages (each with exactly one observe_current_state(question) call). Do not include tool calls in this print-only plan message.

After writing the final step of the plan, write the '<end_plan>' tag and stop there.

Tool signature reference for later verification-only steps (do not call tools now):
```python
{%- for tool in tools.values() %}
{{ tool.to_code_prompt() }}
{% endfor %}
```

---
Now begin! Here is the task to evaluate:
```
{{task}}
```
First write your task analysis, then write your evaluation plan using print() only.""",

    "update_plan_pre_messages": """You are evaluating whether a GUI task has been successfully completed.
You have been given the following task to evaluate:
```
{{task}}
```

Below you will find a history of your evaluation attempts so far.
Review what you've learned and update your evaluation plan accordingly.

Find the task and history below:""",

    "update_plan_post_messages": """Now write your updated analysis and plan (Plan-only print message; if you need additional observations, use separate planning messages each with exactly one observe_current_state(question) call):

## 1. Updated Task Analysis
### 1.1. What we've verified so far
### 1.2. What still needs verification
### 1.3. Updated verification strategy

## 2. Updated Evaluation Plan
Write a step-by-step plan for the remaining verification steps.
Beware that you have {remaining_steps} steps remaining.
After writing the final step, write the '<end_plan>' tag and stop there.

Tool signature reference for later verification-only steps (do not call tools now):
```python
{%- for tool in tools.values() %}
{{ tool.to_code_prompt() }}
{% endfor %}
```

Now write your updated analysis and plan."""
}

# Final answer template for reward evaluation
EVALUATION_FINAL_ANSWER_TEMPLATE = {
    "pre_messages": """You are evaluating whether a GUI task has been successfully completed.
Below is the evaluation history so far:""",
    
    "post_messages": """Based on the above evaluation, provide your final judgment for this task by calling the final_answer tool INSIDE the single required <code> block:
```
{{task}}
```

You MUST output using this exact structure:

Thoughts: <your reasoning about what you will do or inspect next>
<code>
# Call the termination tool to finish the evaluation
final_answer(
  reward=<float between 0 and 1>,
  verdict="Success" or "Partial Success" or "Failure",
  reasoning="<short explanation>"
)
</code>

Rules:
- Follow atomicity: only one tool call inside the <code> block.
- Do NOT output raw JSON anywhere. The tool returns the JSON automatically.
- Exactly one <code> block per message.
- No markdown ``` fences.
- Nothing after </code>.

**Reward Scale:**
- 1.0: Task perfectly completed, all requirements met
- 0.7-0.9: Task mostly completed, minor issues
- 0.4-0.6: Task partially completed, some requirements met
- 0.1-0.3: Task attempted but mostly failed
- 0.0: Task completely failed

**Verdict Guidelines:**
- Success: reward >= 0.7
- Partial Success: 0.3 <= reward < 0.7
- Failure: reward < 0.3
"""
}

# Managed agent template (not used in reward evaluation, but required by smolagents)
EVALUATION_MANAGED_AGENT_TEMPLATE = {
    "task": "",
    "report": ""
}


def get_evaluation_prompt_templates(system_prompt: str) -> dict:
    """
    Get complete prompt templates for reward evaluation.
    
    Args:
        system_prompt: The system prompt to use
        
    Returns:
        Dictionary with all required prompt template keys
    """
    return {
        "system_prompt": system_prompt,
        "planning": EVALUATION_PLANNING_TEMPLATE,
        "final_answer": EVALUATION_FINAL_ANSWER_TEMPLATE,
        "managed_agent": EVALUATION_MANAGED_AGENT_TEMPLATE
    }
