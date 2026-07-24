"""
Get Chrome Font Size tool for RewardAgent.

This tool wraps the desktop_env get_chrome_font_size getter to provide 
read-only access to Chrome's font size settings.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.chrome import get_chrome_font_size


class GetChromeFontSizeTool(Tool):
    """Get Chrome's current font size setting."""
    
    name = "get_chrome_font_size"
    description = (
        "Get the current font size setting in Chrome. "
        "This can help verify if font size was changed correctly. "
        "Returns the current font size value."
    )
    inputs = {}
    output_type = "string"
    
    def __init__(self, env: Any):
        """Initialize with environment object."""
        self.env = env
        super().__init__()
    
    def forward(self) -> str:
        """Get Chrome font size."""
        return self.__call__()
    
    def __call__(self) -> str:
        """Get Chrome's current font size setting."""
        try:
            config = {}
            result = get_chrome_font_size(self.env, config)
            
            if result is None:
                return "Error: Failed to get Chrome font size"
            
            return str(result)
        except Exception as e:
            return f"Error getting Chrome font size: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_chrome_font_size() -> str:\n"
            "    '''Get Chrome's current font size setting.'''\n"
        )
