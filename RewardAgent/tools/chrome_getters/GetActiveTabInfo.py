"""
Get Active Tab Info tool for RewardAgent.

This tool wraps the desktop_env get_active_tab_info getter to provide 
read-only access to Chrome's active tab information.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.chrome import get_active_tab_info


class GetActiveTabInfoTool(Tool):
    """Get information about the currently active tab in Chrome."""
    
    name = "get_active_tab_info"
    description = (
        "Get information about the currently active tab in Chrome. "
        "This can help verify if the correct tab is active or check the current page. "
        "Returns active tab information including URL and title."
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
        """Get active tab info."""
        return self.__call__()
    
    def __call__(self) -> str:
        """
        Get information about the currently active tab in Chrome.
        
        Returns:
            Active tab information as string, or error message
        """
        try:
            config = {}
            result = get_active_tab_info(self.env, config)
            
            if result is None:
                return "Error: Failed to get active tab info"
            
            return str(result)
        except Exception as e:
            return f"Error getting active tab info: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_active_tab_info() -> str:\n"
            "    '''Get information about the currently active tab in Chrome.'''\n"
        )
