"""
Get Bookmarks tool for RewardAgent.

This tool wraps the desktop_env get_bookmarks getter to provide 
read-only access to Chrome's bookmark data.
"""

from smolagents import Tool
from typing import Any, Dict, Optional
import os


from desktop_env.evaluators.getters.chrome import get_bookmarks


class GetBookmarksTool(Tool):
    """Get bookmarks data from Chrome."""
    
    name = "get_bookmarks"
    description = (
        "Get bookmarks data from Chrome. This can help verify if bookmarks were "
        "added, removed, or organized correctly. Optionally filter by bookmark name. "
        "Returns bookmark information as a string."
    )
    inputs = {
        "bookmark_name": {
            "description": "Optional: specific bookmark name to search for",
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
    
    def forward(self, bookmark_name: Optional[str] = None) -> str:
        """Get bookmarks data."""
        return self.__call__(bookmark_name)
    
    def __call__(self, bookmark_name: Optional[str] = None) -> str:
        """
        Get bookmarks data from Chrome.
        
        Args:
            bookmark_name: Optional specific bookmark name to search for
            
        Returns:
            Bookmarks data as string, or error message
        """
        try:
            config = {}
            if bookmark_name:
                config["bookmark_name"] = bookmark_name
                
            result = get_bookmarks(self.env, config)
            
            if result is None:
                return "Error: Failed to get bookmarks data"
            
            return str(result)
        except Exception as e:
            return f"Error getting bookmarks data: {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_bookmarks(bookmark_name: str = None) -> str:\n"
            "    '''Get bookmarks data from Chrome, optionally filtered by name.'''\n"
        )
