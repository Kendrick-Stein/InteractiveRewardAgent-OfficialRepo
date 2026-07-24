"""
Get Cache File tool for RewardAgent.

This tool wraps the desktop_env get_cache_file getter to provide 
read-only access to cached files.
"""

from smolagents import Tool
from typing import Any, Dict
import os


from desktop_env.evaluators.getters.file import get_cache_file


class GetCacheFileTool(Tool):
    """Retrieve a file from the cache directory."""
    
    name = "get_cache_file"
    description = (
        "Retrieve a file from the cache directory. This can help access "
        "previously downloaded or cached files for comparison or verification. "
        "Returns the path to the cached file."
    )
    inputs = {
        "filename": {
            "description": "Name of the cached file to retrieve",
            "type": "string",
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
    
    def forward(self, filename: str) -> str:
        """Get cache file."""
        return self.__call__(filename)
    
    def __call__(self, filename: str) -> str:
        """
        Retrieve a file from the cache directory.
        
        Args:
            filename: Name of the cached file to retrieve
            
        Returns:
            Path to cached file, or error message
        """
        try:
            config = {"path": filename}
            result = get_cache_file(self.env, config)
            
            if result is None:
                return f"Error: Failed to get cache file '{filename}'"
            
            return str(result)
        except Exception as e:
            return f"Error getting cache file '{filename}': {str(e)}"
    
    def to_code_prompt(self) -> str:
        """Return code signature for CodeAgent."""
        return (
            "def get_cache_file(filename: str) -> str:\n"
            "    '''Retrieve a file from the cache directory.'''\n"
        )
