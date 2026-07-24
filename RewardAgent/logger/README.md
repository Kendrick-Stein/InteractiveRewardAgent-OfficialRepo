# RewardAgent Execution Logging

This module provides complete execution logging for RewardAgent, recording every step of the evaluation process in detail.

## Features

- **Tool call recording**: Automatically records every tool invocation, its input parameters, and its return value
- **Execution timing**: Tracks per-step duration and total elapsed time
- **LLM interaction logging**: Optionally records the full conversation history with the LLM
- **Error tracking**: Records all errors raised during execution
- **Structured output**: Saved as JSON for easy analysis and debugging
- **Drop-in integration**: Enabled through parameters, no code changes required

## Quick Start

The logger is a standalone utility: create an `ExecutionLogger`, wrap the tools
you want tracked, and save the log when you are done.

```python
from RewardAgent.logger import ExecutionLogger, wrap_tools_with_logging

# Create a logger and start recording
logger = ExecutionLogger(
    task_instruction="Your task here",
    log_dir="./logs",
)
logger.start_execution()

# Wrap smolagents tools so every call is recorded automatically
logged_tools = wrap_tools_with_logging(tools, logger)

# ... run your evaluation using logged_tools ...

logger.end_execution()
log_path = logger.save_log(include_final_result=result)
print(f"Log saved to: {log_path}")
```

## Log File Format

Logs are saved as JSON with the following structure:

```json
{
  "summary": {
    "task_instruction": "Task description",
    "start_time": "2025-11-28T17:00:00",
    "end_time": "2025-11-28T17:00:30",
    "total_duration": 30.5,
    "total_steps": 10,
    "successful_steps": 9,
    "failed_steps": 1,
    "total_errors": 1
  },
  "execution_steps": [
    {
      "step": 1,
      "timestamp": "2025-11-28T17:00:01",
      "tool_name": "caption_image",
      "inputs": {
        "path_to_image": "step_1.png",
        "question": "What is shown in this image?"
      },
      "output": "The image shows...",
      "duration": 2.3,
      "success": true
    },
    {
      "step": 2,
      "timestamp": "2025-11-28T17:00:05",
      "tool_name": "get_active_url",
      "inputs": {
        "goto_prefix": "https://"
      },
      "output": "https://example.com",
      "duration": 0.5,
      "success": true
    }
  ],
  "llm_interactions": [
    {
      "step": 1,
      "role": "user",
      "content": "...",
      "timestamp": "2025-11-28T17:00:00"
    },
    {
      "step": 1,
      "role": "assistant",
      "content": "...",
      "timestamp": "2025-11-28T17:00:02"
    }
  ],
  "errors": [
    {
      "timestamp": "2025-11-28T17:00:15",
      "error_type": "ToolExecutionError",
      "message": "Failed to execute tool",
      "context": {}
    }
  ],
  "final_result": {
    "reward": 0.9,
    "verdict": "Success",
    "reasoning": "Task completed successfully..."
  }
}
```

## Log Analysis Examples

### Reading and Analyzing Logs

```python
import json

# Read the log file
with open("execution_log_20251128_170000.json", "r") as f:
    log = json.load(f)

# Inspect the execution summary
summary = log["summary"]
print(f"Total steps: {summary['total_steps']}")
print(f"Success rate: {summary['successful_steps'] / summary['total_steps'] * 100}%")
print(f"Total duration: {summary['total_duration']}s")

# Tool usage statistics
from collections import Counter
tool_calls = Counter([step["tool_name"] for step in log["execution_steps"]])
print("\nTool usage:")
for tool, count in tool_calls.most_common():
    print(f"  {tool}: {count} times")

# Find the slowest step
slowest = max(log["execution_steps"], key=lambda x: x["duration"])
print(f"\nSlowest step: {slowest['tool_name']} ({slowest['duration']}s)")
```

## Advanced Usage

### Using ExecutionLogger Directly

For finer-grained control, use the `ExecutionLogger` class directly:

```python
from RewardAgent.logger import ExecutionLogger

# Create a logger
logger = ExecutionLogger(
    task_instruction="My task",
    log_dir="./logs",
    log_level="detailed",  # "simple" or "detailed"
    enable_llm_logging=True
)

# Start execution
logger.start_execution()

# Record a tool call
logger.log_tool_call(
    tool_name="my_tool",
    inputs={"param": "value"},
    output="result",
    duration=1.5,
    success=True
)

# Record an error
logger.log_error(
    error_type="CustomError",
    error_message="Something went wrong",
    context={"additional": "info"}
)

# End execution
logger.end_execution()

# Save the log
log_path = logger.save_log(include_final_result={"reward": 0.8})
print(f"Log saved to: {log_path}")

# Print a summary
logger.print_summary()
```

### Wrapping Custom Tools

Custom tools can be wrapped to enable logging:

```python
from smolagents import Tool
from RewardAgent.logger import ExecutionLogger, create_logged_tool

# Define a custom tool
class MyCustomTool(Tool):
    name = "my_tool"
    description = "Does something useful"
    inputs = {"input": {"type": "string", "description": "Input text"}}
    output_type = "string"

    def forward(self, input: str) -> str:
        return f"Processed: {input}"

# Create a logger
logger = ExecutionLogger("My task", log_dir="./logs")
logger.start_execution()

# Wrap the tool to enable logging
original_tool = MyCustomTool()
logged_tool = create_logged_tool(original_tool, logger)

# Use the wrapped tool (calls are recorded automatically)
result = logged_tool.forward("test input")
```

## Configuration Options

### ExecutionLogger Parameters

- `task_instruction` (str): Task description
- `log_dir` (str | Path | None): Directory for log files; if None, logs are kept in memory only
- `log_level` (str): Logging level, `"simple"` or `"detailed"`
- `enable_llm_logging` (bool): Whether to record LLM interactions

## Performance Considerations

- Logging has minimal performance impact (usually <1% overhead)
- Log file size depends on the number of steps and the size of tool outputs
- Set `enable_llm_logging=False` to reduce log file size
- For large-scale evaluations, periodically clean up old log files

## Troubleshooting

### Log File Not Generated

1. Check that `save_log()` was called after `end_execution()`
2. Ensure `log_dir` is writable
3. Check the console for error messages

### Incomplete Log Content

1. Ensure the evaluation completed normally (no abnormal interruption)
2. Check the `log_level` setting
3. Confirm `enable_llm_logging` matches your expectation

### File Permission Errors

```python
import os
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)
os.chmod(log_dir, 0o755)
```

## Best Practices

1. **Development**: Enable detailed logging (`log_level="detailed"`, `enable_llm_logging=True`)
2. **Production**: Use simplified logging (`log_level="simple"`, `enable_llm_logging=False`)
3. **Batch evaluation**: Use a separate log directory per evaluation
4. **Long-term storage**: Periodically archive or compress old log files
5. **Analysis**: Consider dedicated log-analysis tooling for large volumes of logs
