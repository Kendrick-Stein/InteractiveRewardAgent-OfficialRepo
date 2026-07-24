"""
Get VM Screen Size tool for RewardAgent.

This tool wraps the desktop_env get_vm_screen_size getter to provide 
read-only access to VM screen size information.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.info import get_vm_screen_size


class GetVMScreenSizeTool(Tool):
    """Get the screen size of the VM."""
    
    name = "get_vm_screen_size"
    description = (
        "Get the current screen size (resolution) of the VM. "
        "This can help verify if screen resolution was changed correctly "
        "or check display settings. Returns width and height information."
    )
    inputs = {}
    output_type = "string"
    
    def __init__(self, env: Any):
        """
        Initialize with environment object.
        
        Args:
            env: The desktop environment object (e.g., DesktopEnv instance)
        """
        self.env = env
        super().__init__()
    
    def forward(self) -> str:
        """Get VM screen size."""
        return self.__call__()
    
    def __call__(self) -> str:
        """
        Get the screen size of the VM.
        
        Returns:
            Screen size information as string, or error message
        """
        try:
            config = {}
            result = get_vm_screen_size(self.env, config)
            
            if result is None:
                return "Error: Failed to get VM screen size"
            
            return str(result)
        except Exception as e:
            return f"Error getting VM screen size: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_vm_screen_size() -> str:\n"
            "    '''Get the current screen size (resolution) of the VM.'''\n"
        )
