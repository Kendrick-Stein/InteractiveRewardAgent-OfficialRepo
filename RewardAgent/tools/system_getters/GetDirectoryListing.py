from smolagents import Tool
from desktop_env.evaluators.getters.info import get_list_directory


class GetDirectoryListingTool(Tool):
    name = "get_directory_listing"
    description = """Get a directory tree listing from the virtual machine.
    
    This tool retrieves the directory structure and file listing for a specified path on the virtual machine. Returns a hierarchical view of the directory contents.
    IMPORTANT: You must use a full absolute path (e.g., '/home/user/Desktop'). Tilde expansion ('~') is NOT supported.
    """
    inputs = {
        "path": {
            "type": "string", 
            "description": "The full absolute directory path to list contents for (e.g. '/home/user/Desktop'). Do not use '~'."
        }
    }
    output_type = "object"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, path: str) -> dict:
        """Get directory listing for the specified path.
        
        Args:
            path: The directory path to list
            
        Returns:
            dict: Directory tree structure with files and subdirectories
        """
        try:
            config = {"path": path}
            result = get_list_directory(self.env, config)
            # Check if the result is None (which happens when the path doesn't exist)
            if result is None:
                return {"error": f"Path does not exist. Remember that the path must be on the Virtual Machine (VM), not the host machine."}
            return result
        except Exception as e:
            return {"error": f"Failed to get directory listing: {str(e)}"}

    def __call__(self, path: str) -> dict:
        return self.forward(path)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to get directory listings from the virtual machine.
You must provide the full absolute path. Using '~' is not allowed.
Example usage:
- get_directory_listing(path="/home/user/Desktop")
- get_directory_listing(path="/home/user/Downloads")

The tool returns a dictionary with the directory tree structure."""
