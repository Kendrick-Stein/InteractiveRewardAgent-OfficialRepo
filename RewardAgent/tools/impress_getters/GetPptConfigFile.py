from __future__ import annotations

from smolagents import Tool
from typing import Optional

from desktop_env.evaluators.getters.file import get_vm_file


class GetPptConfigFileTool(Tool):
    name = "get_ppt_config_file"
    description = (
        "Download LibreOffice Impress/Writer configuration file from the VM to the Host cache directory. "
        "Use this before running config-based checks. Returns the Host path to the downloaded file. "
        "If vm_path is not provided, defaults to '/home/user/.config/libreoffice/4/user/registrymodifications.xcu'."
    )
    inputs = {
        "dest": {
            "type": "string",
            "description": (
                "Destination filename to save under the Host cache directory (env.cache_dir). "
                "Example: 'registrymodifications.xcu'"
            ),
        },
    }
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, dest: str) -> str:
        try:
            vm_path = "/home/user/.config/libreoffice/4/user/registrymodifications.xcu"
            dest = dest or "registrymodifications.xcu"
            host_path = get_vm_file(self.env, {"path": vm_path, "dest": dest})
            if not host_path:
                return "Error: Failed to download config file from VM"
            return host_path
        except Exception as e:
            return f"Error: {e}"

    def __call__(self, dest: str) -> str:
        return self.forward( dest)

    def to_code_prompt(self) -> str:
        return (
            "def get_ppt_config_file(dest: str = 'registrymodifications.xcu') -> str:\n"
            "    '''Download LibreOffice config file from VM to Host cache and return the Host path.'''\n"
        )
