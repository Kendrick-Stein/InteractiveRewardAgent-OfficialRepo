"""
Get Chrome Language tool for RewardAgent.

This tool wraps the desktop_env get_chrome_language getter to provide 
read-only access to Chrome's language settings.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.chrome import get_chrome_language


class GetChromeLanguageTool(Tool):
    """Get Chrome's current language setting."""
    
    name = "get_chrome_language"
    description = (
        "Get the current language setting in Chrome. "
        "This can help verify if language settings were changed correctly. "
        "Returns the current language code or name."
    )
    inputs = {}
    output_type = "string"
    
    def __init__(self, env: Any):
        """Initialize with environment object."""
        self.env = env
        super().__init__()
    
    def forward(self) -> str:
        """Get Chrome language."""
        return self.__call__()
    
    def __call__(self) -> str:
        """Get Chrome's current language setting."""
        try:
            config = {}
            result = get_chrome_language(self.env, config)
            
            if result is None:
                return "Error: Failed to get Chrome language"
            
            return str(result)
        except Exception as e:
            return f"Error getting Chrome language: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_chrome_language() -> str:\n"
            "    '''Get Chrome's current language setting.'''\n"
        )
