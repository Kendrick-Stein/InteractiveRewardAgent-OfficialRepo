from smolagents import Tool
from desktop_env.evaluators.getters.info import get_vm_window_size


class GetVMWindowSizeTool(Tool):
    name = "get_vm_window_size"
    description = """Get the window size of a specific application on the virtual machine.
    
    Returns the size (width and height) of the specified application window.
    This tool is useful for understanding the current window dimensions of running applications.
    """
    inputs = {
        "app_class_name": {
            "type": "string", 
            "description": "The class name of the application window to get size for"
        }
    }
    output_type = "object"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, app_class_name: str) -> dict:
        """Get VM window size for the specified application.
        
        Args:
            app_class_name: The class name of the application window
            
        Returns:
            dict: Window size information containing width and height
        """
        try:
            config = {"app_class_name": app_class_name}
            return get_vm_window_size(self.env, config)
        except Exception as e:
            return {"error": f"Failed to get VM window size: {str(e)}"}

    def __call__(self, app_class_name: str) -> dict:
        return self.forward(app_class_name)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to get the window size of a specific application.
Example usage:
- get_vm_window_size(app_class_name="firefox")
- get_vm_window_size(app_class_name="code")

The tool returns a dictionary with window size information."""
