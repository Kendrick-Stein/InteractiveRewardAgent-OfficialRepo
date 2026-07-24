"""
Get Open Tabs Info tool for RewardAgent.

This tool wraps the desktop_env get_open_tabs_info getter to provide 
read-only access to Chrome's open tabs information.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.chrome import get_open_tabs_info


class GetOpenTabsInfoTool(Tool):
    """Get information about currently open tabs in Chrome."""
    
    name = "get_open_tabs_info"
    description = (
        "Get information about all currently open tabs in Chrome. "
        "This can help verify if tabs were opened/closed correctly or check tab content. "
        "Returns tab information including URLs and titles."
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
        """Get open tabs info."""
        return self.__call__()
    
    def __call__(self) -> str:
        """
        Get information about currently open tabs in Chrome.
        
        Returns:
            Open tabs information as string, or error message
        """
        try:
            config = {}
            result = get_open_tabs_info(self.env, config)
            
            if result is None:
                return "Error: Failed to get open tabs info"
            
            return str(result)
        except Exception as e:
            return f"Error getting open tabs info: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_open_tabs_info() -> str:\n"
            "    '''Get information about currently open tabs in Chrome.'''\n"
        )
