from smolagents import Tool
import os


class GetVSCodeWorkspaceFileTool(Tool):
    name = "get_vscode_workspace_file"
    description = (
        "Fetch the VS Code workspace file (/home/user/project.code-workspace) from the VM and cache it on the host. "
        "VM user is fixed to 'user'. The tool does NOT parse the file; use get_vscode_workspace_setting_value_by_intent to read settings."
    )
    inputs = {
        "dest": {
            "type": "string",
            "description": "Destination filename to save in host cache.",
        },
    }
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, dest: str) -> str:
        try:
            vm_path = "/home/user/project.code-workspace"
            controller = getattr(self.env, "controller", None)
            if controller is None:
                return "Error: Missing env.controller"
            file_bytes = controller.get_file(vm_path)
            if file_bytes is None:
                return "Error: Failed to fetch project.code-workspace from VM (file not found or copy failed)"
            os.makedirs(self.env.cache_dir, exist_ok=True)
            host_path = os.path.join(self.env.cache_dir, dest)
            with open(host_path, "wb") as f:
                f.write(file_bytes)
            return host_path
        except Exception as e:
            return f"Error: Failed to get VS Code workspace file: {str(e)}"

    def __call__(self, dest: str) -> str:
        return self.forward(dest=dest)

    def to_code_prompt(self) -> str:
        return (
            f"Use {self.name} to copy the VS Code workspace file from the VM to the host cache.\n"
            "Example:\n"
            "- get_vscode_workspace_file(dest=\"project.code-workspace\")\n"
            "Then use get_vscode_workspace_setting_value_by_intent to read specific settings by intent."
        )
