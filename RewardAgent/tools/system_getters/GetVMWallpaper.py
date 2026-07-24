from smolagents import Tool
from desktop_env.evaluators.getters.info import get_vm_wallpaper


class GetVMWallpaperTool(Tool):
    name = "get_vm_wallpaper"
    description = """Get the current wallpaper from the virtual machine and save it to a file.
    
    This tool captures the current desktop wallpaper and saves it to the specified destination path
    in the environment's cache directory. Returns the path to the saved wallpaper file.
    """
    inputs = {
        "dest": {
            "type": "string", 
            "description": "Destination filename (relative to cache directory) to save the wallpaper"
        }
    }
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, dest: str) -> str:
        """Get VM wallpaper and save it to the specified destination.
        
        Args:
            dest: Destination filename to save the wallpaper
            
        Returns:
            str: Path to the saved wallpaper file
        """
        try:
            config = {"dest": dest}
            return get_vm_wallpaper(self.env, config)
        except Exception as e:
            return f"Error: Failed to get VM wallpaper: {str(e)}"

    def __call__(self, dest: str) -> str:
        return self.forward(dest)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to capture and save the VM's current wallpaper.
Example usage:
- get_vm_wallpaper(dest="current_wallpaper.png")
- get_vm_wallpaper(dest="screenshots/wallpaper.jpg")

The tool returns the path to the saved wallpaper file in the cache directory."""
