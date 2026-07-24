"""
Get Page Info tool for RewardAgent.

This tool wraps the desktop_env get_page_info getter to provide 
read-only access to Chrome's current page information.
"""

from smolagents import Tool
from typing import Any, Dict, Optional
import os


from desktop_env.evaluators.getters.chrome import get_page_info


class GetPageInfoTool(Tool):
    """Get detailed information about the current page in Chrome."""
    
    name = "get_page_info"
    description = (
        "Get detailed information about the current page in Chrome, such as "
        "page title, URL, content, etc. This can help verify if the page "
        "loaded correctly or contains expected content."
    )
    inputs = {
        "info_type": {
            "description": "Type of page info to get (e.g., 'title', 'url', 'content')",
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
    
    def forward(self, info_type: Optional[str] = None) -> str:
        """Get page info."""
        return self.__call__(info_type)
    
    def __call__(self, info_type: Optional[str] = None) -> str:
        """
        Get detailed information about the current page in Chrome.
        
        Args:
            info_type: Optional type of info to get
            
        Returns:
            Page information as string, or error message
        """
        try:
            config = {}
            if info_type:
                config["info_type"] = info_type
                
            result = get_page_info(self.env, config)
            
            if result is None:
                return "Error: Failed to get page info"
            
            return str(result)
        except Exception as e:
            return f"Error getting page info: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_page_info(info_type: str = None) -> str:\n"
            "    '''Get detailed information about the current page in Chrome.'''\n"
        )
