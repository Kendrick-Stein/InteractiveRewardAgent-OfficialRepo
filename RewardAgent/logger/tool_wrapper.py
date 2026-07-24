"""
Tool wrapper for automatic logging of tool calls.

This module provides a wrapper that intercepts tool calls
and logs their inputs, outputs, and execution time.
"""

import time
import types
from typing import Any, Callable, Optional
from smolagents import Tool

from .execution_logger import ExecutionLogger


class LoggedToolWrapper(Tool):
    """
    Wrapper for smolagents Tools that automatically logs all calls.
    
    This wrapper intercepts the forward() method of any Tool and logs:
    - Tool name
    - Input parameters
    - Output/result
    - Execution duration
    - Success/failure status
    """
    
    def __init__(self, original_tool: Tool, logger: ExecutionLogger):
        """
        Initialize the logged tool wrapper.
        
        Args:
            original_tool: The original Tool instance to wrap
            logger: ExecutionLogger instance for recording calls
        """
        self.original_tool = original_tool
        self.logger = logger
        
        # Copy attributes from original tool for smolagents compatibility
        self.name = original_tool.name
        self.description = original_tool.description
        self.inputs = getattr(original_tool, 'inputs', {})
        self.output_type = getattr(original_tool, 'output_type', 'string')
        
        # Call parent constructor
        super().__init__()
        
        # Install a signature-preserving forward method matching tool.inputs
        self._install_signature_forward()
        
    def forward(self, *args, **kwargs) -> Any:
        """
        This placeholder is replaced at runtime with a signature-preserving
        method whose parameters exactly match self.inputs keys.
        """
        raise NotImplementedError("LoggedToolWrapper forward not initialized")

    def _invoke_and_log(self, **call_kwargs) -> Any:
        """
        Invoke the original tool with keyword args, while timing and logging the call.
        """
        start_time = time.time()
        success = True
        error = None
        output = None
        try:
            output = self.original_tool.forward(**call_kwargs)
        except Exception as e:
            success = False
            error = str(e)
            output = f"Error: {str(e)}"
            raise
        finally:
            duration = time.time() - start_time
            self.logger.log_tool_call(
                tool_name=self.name,
                inputs=call_kwargs,
                output=output,
                duration=duration,
                success=success,
                error=error,
            )
        return output

    def _install_signature_forward(self):
        """
        Dynamically install a forward(self, <named params>) with parameters matching inputs keys.
        """
        # Determine ordered parameter names
        if isinstance(self.inputs, dict):
            param_names = list(self.inputs.keys())
        else:
            param_names = []
        if param_names:
            params_sig = ", ".join(param_names)
            kwargs_build = "{" + ", ".join([f"'{k}': {k}" for k in param_names]) + "}"
            src = (
                "def _generated_forward(self, " + params_sig + "):\n"
                "    call_kwargs = " + kwargs_build + "\n"
                "    return self._invoke_and_log(**call_kwargs)\n"
            )
        else:
            src = (
                "def _generated_forward(self):\n"
                "    return self._invoke_and_log()\n"
            )
        ns = {}
        exec(src, {}, ns)
        generated = ns["_generated_forward"]
        # Bind as instance method
        self.forward = types.MethodType(generated, self)
        
    def _prepare_inputs_for_logging(self, args: tuple, kwargs: dict) -> dict:
        """
        Prepare input parameters for logging.
        
        Args:
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Dictionary of input parameters
        """
        inputs = {}
        
        # Add positional args with generic names
        for i, arg in enumerate(args):
            inputs[f"arg_{i}"] = arg
            
        # Add keyword args
        inputs.update(kwargs)
        
        return inputs
        
    def __call__(self, *args, **kwargs) -> Any:
        """
        Make the wrapper callable like the original tool.
        
        Returns:
            Result from forward() method
        """
        return self.forward(*args, **kwargs)
        
    def to_code_prompt(self) -> str:
        """
        Return the code prompt from the original tool.
        
        This ensures CodeAgent can properly understand the tool's interface.
        
        Returns:
            Code prompt string
        """
        if hasattr(self.original_tool, 'to_code_prompt'):
            return self.original_tool.to_code_prompt()
        
        # Fallback: generate basic prompt
        return (
            f"def {self.name}(...) -> {self.output_type}:\n"
            f"    '''{self.description}'''\n"
        )


def create_logged_tool(tool: Tool, logger: ExecutionLogger) -> LoggedToolWrapper:
    """
    Create a logged version of a tool.
    
    This is a convenience function for wrapping tools with logging.
    
    Args:
        tool: Original Tool instance
        logger: ExecutionLogger for recording calls
        
    Returns:
        LoggedToolWrapper instance
        
    Example:
        ```python
        logger = ExecutionLogger("My task")
        original_tool = CaptionImageTool()
        logged_tool = create_logged_tool(original_tool, logger)
        
        # Now all calls to logged_tool will be automatically logged
        result = logged_tool.forward("image.png", "What's in this image?")
        ```
    """
    return LoggedToolWrapper(tool, logger)


def wrap_tools_with_logging(
    tools: list[Tool],
    logger: ExecutionLogger,
) -> list[LoggedToolWrapper]:
    """
    Wrap multiple tools with logging.
    
    Args:
        tools: List of Tool instances
        logger: ExecutionLogger for recording calls
        
    Returns:
        List of LoggedToolWrapper instances
        
    Example:
        ```python
        logger = ExecutionLogger("My task")
        tools = [CaptionImageTool(), GetActiveURLTool(env)]
        logged_tools = wrap_tools_with_logging(tools, logger)
        ```
    """
    return [create_logged_tool(tool, logger) for tool in tools]
