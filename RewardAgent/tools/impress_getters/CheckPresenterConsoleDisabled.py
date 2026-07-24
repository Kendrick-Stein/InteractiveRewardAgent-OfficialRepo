from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_presenter_console_disable


class CheckPresenterConsoleDisabledTool(Tool):
    name = "check_presenter_console_disabled"
    description = (
        "Check if LibreOffice Impress Presenter Console is disabled using a config (.xcu) file on the Host. "
        "Use get_ppt_config_file first if the config is inside the VM to download it to Host. "
        "Returns 1 if EnablePresenterScreen is False (disabled), else 0."
    )
    inputs = {
        "config_file_path": {
            "type": "string",
            "description": (
                "Host path to LibreOffice config file (registrymodifications.xcu). "
                "Do not pass VM paths; use get_ppt_config_file to download first if needed."
            ),
        },
    }
    output_type = "number"

    def forward(self, config_file_path: str) -> float:
        try:
            return float(check_presenter_console_disable(config_file_path))
        except Exception:
            return 0.0

    def __call__(self, config_file_path: str) -> float:
        return self.forward(config_file_path)

    def to_code_prompt(self) -> str:
        return (
            "def check_presenter_console_disabled(config_file_path: str) -> float:\n"
            "    '''Return 1.0 if Presenter Console is disabled in config, else 0.0.\n"
            "    Note: config_file_path must be a Host path (download with get_ppt_config_file if needed).'''\n"
        )
