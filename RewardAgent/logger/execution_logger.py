"""
ExecutionLogger: Comprehensive execution logging for RewardAgent.

This module provides detailed logging of:
- Tool calls and their results
- LLM interactions
- Execution timeline and duration
- Error tracking
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ExecutionLogger:
    """
    Logger for tracking RewardAgent execution details.
    
    Records all tool calls, LLM interactions, and execution metadata
    in a structured format for analysis and debugging.
    """
    
    def __init__(
        self,
        task_instruction: str,
        log_dir: Optional[Union[str, Path]] = None,
        log_level: str = "detailed",
        enable_llm_logging: bool = True,
    ):
        """
        Initialize the execution logger.
        
        Args:
            task_instruction: The task being evaluated
            log_dir: Directory to save logs (if None, logs are only kept in memory)
            log_level: "simple" or "detailed" logging
            enable_llm_logging: Whether to log LLM interactions
        """
        self.task_instruction = task_instruction
        self.log_dir = Path(log_dir) if log_dir else None
        self.log_level = log_level
        self.enable_llm_logging = enable_llm_logging
        
        # Execution tracking
        self.start_time = None
        self.end_time = None
        self.execution_steps: List[Dict[str, Any]] = []
        self.llm_interactions: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Step counter
        self.step_counter = 0
        
    def start_execution(self):
        """Mark the start of execution."""
        self.start_time = datetime.now()
        
    def end_execution(self):
        """Mark the end of execution."""
        self.end_time = datetime.now()
        
    def log_tool_call(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        output: Any,
        duration: float,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Log a tool call.
        
        Args:
            tool_name: Name of the tool being called
            inputs: Input parameters to the tool
            output: Tool's output/result
            duration: Execution time in seconds
            success: Whether the call succeeded
            error: Error message if failed
        """
        self.step_counter += 1
        
        step_info = {
            "step": self.step_counter,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "inputs": self._sanitize_for_json(inputs),
            "output": self._sanitize_for_json(output),
            "duration": round(duration, 3),
            "success": success,
        }
        
        if error:
            step_info["error"] = str(error)
            
        self.execution_steps.append(step_info)
        
    def log_llm_interaction(
        self,
        role: str,
        content: Any,
        step: Optional[int] = None,
    ):
        """
        Log an LLM interaction (user/assistant messages).
        
        Args:
            role: "user" or "assistant"
            content: Message content
            step: Associated step number (optional)
        """
        if not self.enable_llm_logging:
            return
            
        interaction = {
            "step": step or self.step_counter,
            "role": role,
            "content": self._sanitize_for_json(content),
            "timestamp": datetime.now().isoformat(),
        }
        
        self.llm_interactions.append(interaction)
        
    def log_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Log an error.
        
        Args:
            error_type: Type/category of error
            error_message: Detailed error message
            context: Additional context information
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": str(error_message),
        }
        
        if context:
            error_info["context"] = self._sanitize_for_json(context)
            
        self.errors.append(error_info)
        
    def get_log_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the execution log.
        
        Returns:
            Dictionary containing execution summary
        """
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        summary = {
            "task_instruction": self.task_instruction,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": round(duration, 3) if duration else None,
            "total_steps": len(self.execution_steps),
            "successful_steps": sum(1 for s in self.execution_steps if s["success"]),
            "failed_steps": sum(1 for s in self.execution_steps if not s["success"]),
            "total_errors": len(self.errors),
        }
        
        return summary
        
    def get_full_log(self) -> Dict[str, Any]:
        """
        Get the complete execution log.
        
        Returns:
            Dictionary containing all logged information
        """
        log = {
            "summary": self.get_log_summary(),
            "execution_steps": self.execution_steps,
        }
        
        if self.enable_llm_logging:
            log["llm_interactions"] = self.llm_interactions
            
        if self.errors:
            log["errors"] = self.errors
            
        return log
        
    def save_log(
        self,
        filename: Optional[str] = None,
        include_final_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Path]:
        """
        Save the execution log to a JSON file.
        
        Args:
            filename: Custom filename (auto-generated if None)
            include_final_result: Final evaluation result to include
            
        Returns:
            Path to saved log file, or None if log_dir not set
        """
        if not self.log_dir:
            return None
            
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"execution_log_{timestamp}.json"
            
        log_path = self.log_dir / filename
        
        # Build complete log
        log_data = self.get_full_log()
        
        if include_final_result:
            log_data["final_result"] = include_final_result
            
        # Save to file
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
            
        return log_path
        
    def _sanitize_for_json(self, obj: Any) -> Any:
        """
        Sanitize objects for JSON serialization.
        
        Args:
            obj: Object to sanitize
            
        Returns:
            JSON-serializable version of the object
        """
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
            
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
            
        if isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
            
        if isinstance(obj, Path):
            return str(obj)
            
        if isinstance(obj, datetime):
            return obj.isoformat()
            
        # For complex objects, try to convert to string
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__} object>"
            
    def print_summary(self):
        """Print a human-readable summary to console."""
        summary = self.get_log_summary()
        
        print("\n" + "="*60)
        print("EXECUTION LOG SUMMARY")
        print("="*60)
        print(f"\nTask: {summary['task_instruction']}")
        print(f"Duration: {summary['total_duration']}s" if summary['total_duration'] else "Duration: N/A")
        print(f"\nTotal Steps: {summary['total_steps']}")
        print(f"  ✓ Successful: {summary['successful_steps']}")
        print(f"  ✗ Failed: {summary['failed_steps']}")
        
        if summary['total_errors'] > 0:
            print(f"\n⚠️  Total Errors: {summary['total_errors']}")
            
        print("="*60 + "\n")
