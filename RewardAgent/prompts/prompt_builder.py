"""
Dynamic prompt builder for RewardAgent.

Constructs system prompts that adapt based on available inputs
(trajectory images, environment object, etc.).
"""

from typing import Optional


def build_evaluation_prompt(
    base_prompt: str,
    has_trajectory: bool = False,
    has_env: bool = False
) -> str:
    """
    Build a dynamic system prompt based on available evaluation inputs.
    
    Args:
        base_prompt: The base system prompt template
        has_trajectory: Whether trajectory images are available
        has_env: Whether environment object is available
        
    Returns:
        Enhanced system prompt with mode-specific guidance
    """
    
    # Start with base prompt
    prompt_parts = [base_prompt]
    
    # Add mode-specific guidance
    prompt_parts.append("\n---\n\n### 🎯 EVALUATION MODE\n")
    
    if has_trajectory and has_env:
        prompt_parts.append(_get_hybrid_mode_guidance())
    elif has_trajectory and not has_env:
        prompt_parts.append(_get_trajectory_only_guidance())
    elif has_env and not has_trajectory:
        prompt_parts.append(_get_env_only_guidance())
    else:
        prompt_parts.append(_get_minimal_guidance())
    
    # Add protocol rules and criterion-centric workflow reminder
    prompt_parts.append(_get_protocol_rules())
    
    # Add final output reminder
    prompt_parts.append(_get_output_format_reminder())
    
    return "".join(prompt_parts)


def _get_hybrid_mode_guidance() -> str:
    """Guidance for hybrid mode (trajectory + env)."""
    return """
**HYBRID MODE** (Trajectory + Environment Available)

You have access to both visual trajectory evidence and live environment state.
Use a two-stage evaluation strategy:

**Stage 1: Trajectory Analysis**
1. Use `retrieve_image()` to get all trajectory screenshots
2. Use `caption_image()` to analyze key frames, especially:
   - Initial state (step_1.png)
   - Final state (last step)
   - Steps with significant visual changes (low similarity scores)
3. Examine action sequences and visual changes
4. Form preliminary hypothesis about task completion

**Stage 2: Environment Verification**
1. Use environment tools to verify your hypothesis:
   - `execute_vm_command()` to check file existence, process status, etc.
   - `get_vm_file()` to inspect file contents
   - `get_terminal_output()` to review command history
2. Cross-validate visual observations with actual state
3. Look for discrepancies between what appears done vs. what is actually done

**Evaluation Strategy:**
- Visual evidence shows WHAT happened
- Environment state confirms WHETHER it succeeded
- Combine both for robust assessment
- If they conflict, environment state is ground truth

**Example Workflow:**
1. Retrieve and analyze trajectory images
2. Identify expected final state from task instruction
3. Use environment tools to verify that state exists
4. Assign reward based on verification results
"""


def _get_trajectory_only_guidance() -> str:
    """Guidance for trajectory-only mode."""
    return """
**TRAJECTORY-ONLY MODE** (No Environment Access)

You can only analyze visual evidence from trajectory screenshots.
Use careful visual reasoning:

**Analysis Strategy:**
1. Use `retrieve_image()` to get all screenshots
2. Analyze the sequence:
   - Initial state: What was the starting condition?
   - Action progression: Do actions align with task requirements?
   - Visual changes: Do changes match expected outcomes?
   - Final state: Does it match task goal?
3. Use `caption_image()` extensively to:
   - Describe UI states
   - Identify specific elements (buttons, text, files, etc.)
   - Detect errors or unexpected states
   - Compare before/after states

**Key Indicators:**
- **Success signals**: 
  - Actions directly address task requirements
  - Visual changes align with expected outcomes
  - Final state shows completed task elements
  - No error messages or unexpected states
  
- **Failure signals**:
  - Actions don't match task requirements
  - High similarity scores (no changes when changes expected)
  - Error dialogs or warning messages
  - Final state missing expected elements

**Limitations:**
- Cannot verify actual file contents (only visual appearance)
- Cannot check system state beyond what's visible
- Must infer completion from visual evidence alone
- Be conservative: if uncertain, assign lower reward

**Example Workflow:**
1. Retrieve all trajectory images
2. Caption first and last images to understand start/end states
3. Identify critical intermediate steps
4. Caption those steps to verify action execution
5. Compare final state against task requirements
6. Assign reward based on visual evidence
"""


def _get_env_only_guidance() -> str:
    """Guidance for environment-only mode."""
    return """
**ENVIRONMENT-ONLY MODE** (No Trajectory Available)

You can only query the current environment state.
Use direct verification:

**Verification Strategy:**
1. Parse task instruction to identify expected outcomes:
   - Files that should exist
   - Content that should be present
   - Processes that should be running
   - System state that should be achieved

2. Use environment tools to verify each requirement:
   - `execute_vm_command()` to check existence/status
   - `get_vm_file()` to inspect file contents
   - `get_terminal_output()` to review recent activity

3. Compare actual state vs. expected state

**Example Workflow:**
For task "Create a file named test.txt with content 'Hello World'":
1. Check file exists: `execute_vm_command("ls /path/to/test.txt")`
2. Verify content: `get_vm_file("/path/to/test.txt", "test.txt")` then read it
3. Assign reward based on verification

**Limitations:**
- No visual context of how task was executed
- Cannot see if user struggled or made errors
- Only final state is available
- Cannot assess execution quality, only outcome
"""


def _get_minimal_guidance() -> str:
    """Guidance when neither trajectory nor env is available."""
    return """
**MINIMAL MODE** (No Trajectory or Environment)

⚠️ **Warning**: You have no tools to verify task completion.
You can only provide reasoning based on the task instruction itself.

In this mode:
1. Acknowledge the limitation in your reasoning
2. Explain what would need to be verified
3. Assign a neutral reward (0.5) with explanation
4. Recommend providing trajectory or environment for proper evaluation
"""


def _get_output_format_reminder() -> str:
    """Reminder about output format."""
    return """

---

### 📤 OUTPUT FORMAT (CRITICAL)

You MUST output your final judgment in this EXACT JSON format:

```json
{
  "reward": <float between 0 and 1>,
  "verdict": "<Success|Partial Success|Failure>",
  "reasoning": "<detailed explanation>"
}
```

**Reward Scale:**
- **1.0**: Task perfectly completed, all requirements met
- **0.7-0.9**: Task mostly completed, minor issues or missing optional elements
- **0.4-0.6**: Task partially completed, some requirements met
- **0.1-0.3**: Task attempted but mostly failed, few requirements met
- **0.0**: Task completely failed, no requirements met

**Verdict Guidelines:**
- **Success**: reward >= 0.7
- **Partial Success**: 0.3 <= reward < 0.7
- **Failure**: reward < 0.3

**Reasoning Requirements:**
- Be specific about what was verified
- Cite evidence (tool outputs, visual observations)
- Explain why the reward was assigned
- Note any ambiguities or limitations
"""

def _get_protocol_rules() -> str:
    """Criterion-centric protocol and tool usage rules (merged observation)."""
    return """

---

### 📐 CRITERION-CENTRIC WORKFLOW AND PROTOCOL (IMPORTANT)

You must organize evaluation around verifiable criteria and alternate between Plan and Verify steps for each criterion.

1) Criteria Definition (MANDATORY; optional read-only observations allowed)
- Optional Observations (as preparatory sub-steps):
  You MAY perform read-only observations during planning to capture current UI context without side effects. Each planning message MUST contain exactly one <code> block and at most one tool call; if it calls a tool, it MUST be observe_current_state(question).
  <code>
  observe_current_state("Describe the screen, visible apps and windows, and any key indicators relevant to evaluation.")
  </code>
- After observations (if used), you MUST output the criteria list in a separate planning message using ONLY print() statements (no tools, no JSON, no imports).

2) Iterative Plan ↔ Verify per Criterion
- Planning messages: observe-then-print. You MAY perform read-only observe_current_state(question) calls during planning as many times as needed; each observation must be in its own planning message with at most one tool call. Emit criteria and the verification plan via print() in separate planning messages (no JSON, no imports, no file I/O).
- Verification messages: STRICT ATOMICITY — exactly ONE tool call inside the single <code> block; no additional code or multiple tools.
- If one evidence path fails for a criterion, you may try alternative evidence paths; failing one path does NOT imply overall task failure.

3) Computer Use Policy
- Prefer read-only tools (e.g., observation, environment getters). Use interactive/side-effecting tools only when necessary.

4) Host vs VM Path Handling
- For any Python-based analysis on host, transfer artifacts from VM to host first using the appropriate file getter tools.

Tool Signature Reference:
- observe_current_state(question: str) -> str  # returns a JSON string with captioned UI state

Follow these rules consistently across the evaluation.
"""
