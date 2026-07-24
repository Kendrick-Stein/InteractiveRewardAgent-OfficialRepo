"""
Environment getter tools for RewardAgent.

These tools wrap the desktop_env getters to provide read-only access
to the GUI environment state for verification purposes.
"""

from smolagents import Tool
from typing import Any, Optional
import os


from desktop_env.evaluators.getters.general import (
    get_vm_command_line,
    get_vm_command_error,
    get_vm_terminal_output
)
from desktop_env.evaluators.getters.file import (
    get_vm_file,
    get_cache_file
)

from desktop_env.evaluators.getters.chrome import (
    get_active_url_from_accessTree,
    get_enabled_experiments
)


class VMActiveTabUrlTool(Tool):
    """Get the URL of the active tab from the browser accessibility tree."""
    
    name = "get_active_tab_url"
    description = (
        "Get the URL of the active tab from the browser accessibility tree. "
        "This tool is useful when you need to determine which page is currently active in the browser without direct API access. "
        "Returns the URL as a string."
    )
    inputs = {
        "goto_prefix": {
            "description": "The prefix to add to the URL (default: 'https://')",
            "type": "string",
            "nullable": True,
        }
    }
    output_type = "string"
    
    def __init__(self, env: Any):
        """
        Initialize with environment object.
        
        Args:
            env: The desktop environment object (e.g., DesktopEnv instance)
        """
        self.env = env
        super().__init__()
    
    def forward(self, goto_prefix: Optional[str] = "https://") -> str:
        """Get active tab URL and return it."""
        return self.__call__(goto_prefix)
    
    def __call__(self, goto_prefix: Optional[str] = "https://") -> str:
        """
        Get the URL of the active tab from the browser accessibility tree.
        
        Args:
            goto_prefix: The prefix to add to the URL (default: "https://")
            
        Returns:
            The URL of the active tab as a string, or error message
        """
        try:
            config = {"goto_prefix": goto_prefix} if goto_prefix else {}
            result = get_active_url_from_accessTree(self.env, config)
            
            if result is None:
                return "Error: Failed to get the active tab URL"
            
            return str(result)
        except Exception as e:
            return f"Error getting active tab URL: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_active_tab_url(goto_prefix: str = 'https://') -> str:\n"
            "    '''Get the URL of the active tab from the browser accessibility tree. "
            "Returns the URL as a string.'''\n"
        )

class VMEnabledExperimentsTool(Tool):
    """Get the enabled experiments from Chrome/Chromium browser."""
    
    name = "get_enabled_experiments"
    description = (
        "Get the list of enabled experiments from Chrome/Chromium browser. "
        "This tool reads the browser's Local State file to retrieve the enabled labs experiments. "
        "Returns a list of enabled experiment names."
    )
    inputs = {}
    # "list" is not a valid smolagents output_type; use "array"
    output_type = "array"
    
    def __init__(self, env: Any):
        """
        Initialize with environment object.
        
        Args:
            env: The desktop environment object (e.g., DesktopEnv instance)
        """
        self.env = env
        super().__init__()
    
    def forward(self) -> list:
        """Get enabled experiments and return them."""
        return self.__call__()
    
    def __call__(self) -> list:
        """
        Get the list of enabled experiments from Chrome/Chromium browser.
        
        Returns:
            A list of enabled experiment names, or an empty list on error
        """
        try:
            config = {}
            result = get_enabled_experiments(self.env, config)
            
            return result
        except Exception as e:
            print(f"Error getting enabled experiments: {str(e)}")  # log the error but return an empty list
        return []
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_enabled_experiments() -> list:\n"
            "    '''Get the list of enabled experiments from Chrome/Chromium browser. "
            "Returns a list of enabled experiment names.'''\n"
        )