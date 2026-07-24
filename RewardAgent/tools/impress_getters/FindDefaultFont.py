from smolagents import Tool
from desktop_env.evaluators.metrics.docs import find_default_font


class FindDefaultFontTool(Tool):
    name = "find_default_font"
    description = (
        "Check LibreOffice Writer default font from a config (.xcu) file located on the Host. "
        "Use get_ppt_config_file first if the config is inside the VM to download it to Host. "
        "Returns 1 if the default font equals the expected font_name, else 0."
    )
    inputs = {
        "config_file_path": {
            "type": "string",
            "description": (
                "Host path to LibreOffice config file (e.g., registrymodifications.xcu). "
                "Do not pass VM paths; use get_ppt_config_file to download first if needed."
            ),
        },
        "font_name": {
            "type": "string",
            "description": "Expected default font name (e.g., 'Liberation Serif').",
        },
    }
    output_type = "number"

    def forward(self, config_file_path: str, font_name: str) -> float:
        try:
            rules = {"font_name": font_name}
            return float(find_default_font(config_file_path, rules))
        except Exception:
            return 0.0

    def __call__(self, config_file_path: str, font_name: str) -> float:
        return self.forward(config_file_path, font_name)

    def to_code_prompt(self) -> str:
        return (
            "def find_default_font(config_file_path: str, font_name: str) -> float:\n"
            "    '''Return 1.0 if LibreOffice Writer default font equals font_name, else 0.0.\n"
            "    Note: config_file_path must be a Host path (download from VM with get_ppt_config_file if needed).'''\n"
        )
