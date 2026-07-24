# RewardAgent - GUI Task Evaluation System

A sophisticated reward evaluation agent for GUI tasks that combines visual trajectory analysis with live environment verification, organized around criterion-centric Plan↔Verify alternation with an optional read-only observation capability.

## 🎯 Overview

RewardAgent is built on top of `smolagents.CodeAgent` and provides a flexible evaluation framework that can:

- **Analyze visual trajectories**: Process screenshot sequences to understand task execution
- **Verify environment state**: Query live GUI environments to confirm task completion
- **Hybrid evaluation**: Combine both approaches for robust assessment
- **Dynamic tool selection**: Automatically configure tools based on available inputs

## 🏗️ Architecture

### Core Components

```
RewardAgent/
├── agent.py                    # Main RewardAgent class with evaluate() method
├── prompts/
│   ├── system_prompt.py       # Base system prompt template (criterion-centric protocol)
│   ├── prompt_builder.py      # Dynamic prompt construction + protocol reminder
│   └── evaluation_templates.py# Planning/Final templates for evaluation
├── tools/
│   ├── CaptionImage.py        # Vision-based image analysis (captioning screenshots)
│   ├── ObserveCurrentState.py # Read-only screenshot+caption tool (no side effects)
│   └── environment_tools.py   # Environment state getters (read-only)
└── llm_engine/
    └── gpt_engine.py          # LLM backend integration
```

### Evaluation Modes

1. **Trajectory-Only Mode**: Analyze visual evidence from screenshots
2. **Environment-Only Mode**: Query live environment state
3. **Hybrid Mode**: Combine both for maximum reliability

### Protocol: Criteria Definition + Optional Read-Only Observations; Iterative Plan ↔ Verify

RewardAgent’s evaluation flow is criterion-centric:

- Criteria Definition (MANDATORY): The agent defines concrete, verifiable criteria for success.
- Optional Observations (as a means, not a stage): The agent may perform read-only observations using observe_current_state(question) during planning as many times as needed to refine criteria. Each observation is a separate planning message with exactly one tool call; criteria and verification plans are emitted via print() in separate planning messages. Observations have no side effects and are optional.
- Iterative Plan ↔ Verify per Criterion:
  - Plan messages: use print() only, no tool calls, no JSON, no imports.
  - Verify messages: exactly one tool call inside a single <code> block (atomic verification). If one evidence path fails, the agent may try alternative evidence paths; a single failed path does not imply task failure.
  - Prefer read-only tools (observation and environment getters). Use interactive, side-effecting tools only when strictly necessary.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API key
```

### Basic Usage

```python
from desktop_env.desktop_env import DesktopEnv
from RewardAgent.agent import RewardAgent
from RewardAgent.llm_engine.gpt_engine import DeerapiEngine

# Initialize environment and agent (env is required)
env = DesktopEnv(action_space="pyautogui", provider_name="docker_server", os_type="Ubuntu")
llm = DeerapiEngine(api_key="your-api-key", model_id="gpt-4o")
agent = RewardAgent(llm=llm, env=env, max_iterations=6)

# Evaluate using trajectory
result = agent.evaluate(
    task_instruction="Please help me increase the indent of line 2 to line 10 by one tab.",
    apps=["libreoffice_writer"],
    trajectory_dir="./path/to/trajectory"
)

print(result)
# {
#   "reward": 0.95,
#   "verdict": "Success",
#   "reasoning": "The task was completed successfully..."
# }
```

## 📖 Detailed Usage

### 1. Trajectory-Only Evaluation

Best for: Offline analysis, when environment is no longer available

```python
result = agent.evaluate(
    task_instruction="Create a new file named test.txt",
    apps=["os"],
    trajectory_dir="./path/to/trajectory"
)
```

**Available Tools:**
- `retrieve_image(path_to_trajectory)`: Get list of screenshot paths
- `caption_image(path_to_image, question)`: Analyze images with vision model
 - `observe_current_state(question)`: Read-only capture and caption of the current UI state (optional, no side effects; can be used multiple times during planning)

**Evaluation Strategy:**
1. Retrieve all trajectory screenshots
2. Analyze initial and final states
3. Examine action sequences and visual changes
4. Infer completion from visual evidence

### 2. Hybrid Evaluation (Recommended)

Best for: Maximum reliability, when both trajectory and environment are available

```python
# The environment is provided at construction time (see Basic Usage).
# Evaluate with both trajectory and the live environment:
result = agent.evaluate(
    task_instruction="Create a file named test.txt with content 'Hello World'",
    apps=["os"],
    trajectory_dir="./path/to/trajectory"
)
```

**Available Tools:**
- All trajectory tools (retrieve_image, caption_image)
 - `observe_current_state(question)`: Read-only capture and caption of the current UI state (can be used multiple times during planning)
- `execute_vm_command(command, shell)`: Execute read-only commands
- `get_vm_file(vm_path, dest_name)`: Retrieve files for inspection
- `get_terminal_output()`: Get terminal history
- `get_vm_command_error(command, shell)`: Get command error output

**Evaluation Strategy:**
1. **Stage 1 - Trajectory Analysis**: Understand what happened visually
2. **Stage 2 - Environment Verification**: Confirm actual state matches expectations
3. Cross-validate findings from both sources

### 3. Environment-Only Evaluation

Best for: When only final state matters, no trajectory available

```python
result = agent.evaluate(
    task_instruction="Create a file named test.txt",
    apps=["os"],  # no trajectory_dir: environment-only evaluation
)
```

**Available Tools:**
- All environment getter tools

**Evaluation Strategy:**
1. Parse task requirements
2. Query environment to verify each requirement
3. Compare actual vs expected state

## 🛠️ Environment Tools

### VMCommandLineTool

Execute read-only commands to check system state.

```python
# Example usage within agent evaluation
execute_vm_command("ls /home/user/Desktop", shell=False)
execute_vm_command("cat /path/to/file.txt", shell=False)
execute_vm_command("ps aux | grep process_name", shell=True)
```

### VMFileTool

Retrieve files from VM for content inspection.

```python
# Downloads file to cache and returns local path
local_path = get_vm_file(
    vm_path="/home/user/Desktop/test.txt",
    dest_name="test.txt"
)
```

### VMTerminalOutputTool

Get terminal output history.

```python
output = get_terminal_output()
```

### VMCommandErrorTool

Get error output from command execution.

```python
error = get_vm_command_error("invalid_command", shell=False)
```

## 📊 Output Format

All evaluations return a structured dictionary:

```python
{
    "reward": float,      # 0.0 to 1.0
    "verdict": str,       # "Success" | "Partial Success" | "Failure"
    "reasoning": str      # Detailed explanation
}
```

### Reward Scale

- **1.0**: Perfect completion, all requirements met
- **0.7-0.9**: Mostly complete, minor issues
- **0.4-0.6**: Partially complete, some requirements met
- **0.1-0.3**: Mostly failed, few requirements met
- **0.0**: Complete failure

### Verdict Guidelines

- **Success**: reward ≥ 0.7
- **Partial Success**: 0.3 ≤ reward < 0.7
- **Failure**: reward < 0.3

## 🎨 Advanced Features

### Custom Max Iterations

```python
agent = RewardAgent(llm=llm, env=env, max_iterations=10)  # set at construction time
```

### Error Handling

```python
try:
    result = agent.evaluate(
        task_instruction="Task description",
        apps=["os"],
        trajectory_dir="./path"
    )
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Evaluation failed: {e}")
```

## 🔧 Configuration

### System Prompt Customization

```python
from RewardAgent.prompts.system_prompt import system_prompt

# Customize base prompt
custom_prompt = system_prompt + "\n\nAdditional instructions..."

agent = RewardAgent(
    llm=llm,
    env=env,
    system_prompt=custom_prompt,
    max_iterations=6
)
```

### LLM Backend

Currently supports OpenAI-compatible APIs via `DeerapiEngine`:

```python
from RewardAgent.llm_engine.gpt_engine import DeerapiEngine

llm = DeerapiEngine(
    api_key="your-key",  # or None to read IRA_API_KEY from the environment
    model_id="gpt-4o"    # or "gpt-4o-mini", "gpt-5", etc.
)
```

The endpoint base URL is read from `IRA_BASE_URL` in the environment (see the
repository root `.env.example`).

## 🤝 Contributing

When adding new tools or environment getters:

1. Create tool wrapper in `tools/` (e.g., `environment_tools.py` for env getters)
2. Inherit from `smolagents.Tool`
3. Implement `__init__(env)`, `forward()`, and `to_code_prompt()`
4. Add to dynamic tool selection in `agent.py`

Tool signature reference used by prompts:
- observe_current_state(question: str) -> str

Protocol constraints enforced by system prompt:
- Planning messages follow observe-then-print: you may perform multiple read-only observe_current_state(question) calls during planning (one tool call per planning message). Emit criteria and the verification plan via print() in separate planning messages. Verification messages must contain exactly one tool call inside a single <code> block; finalization is via the final_answer tool.

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

Built on top of:
- [smolagents](https://github.com/huggingface/smolagents) - Agent framework
- [desktop-env](https://github.com/xlang-ai/OSWorld) - GUI environment
