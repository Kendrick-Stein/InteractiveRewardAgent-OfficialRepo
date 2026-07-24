from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_auto_saving_time


class CheckAutoSavingTimeTool(Tool):
    name = "check_auto_saving_time"
    description = (
        "Check LibreOffice autosave time interval in a config (.xcu) file located on the Host. "
        "Use get_ppt_config_file first if the config is inside the VM to download it to Host. "
        "Returns 1 if AutoSaveTimeIntervall equals the given minutes, else 0."
    )
    inputs = {
        "config_file_path": {
            "type": "string",
            "description": (
                "Host path to LibreOffice config file (registrymodifications.xcu). "
                "Do not pass VM paths; use get_ppt_config_file to download first if needed."
            ),
        },
        "minutes": {
            "type": "integer",
            "description": "Expected autosave interval in minutes (int).",
        },
    }
    output_type = "number"

    def forward(self, config_file_path: str, minutes: int) -> float:
        try:
            rules = {"minutes": int(minutes)}
            return float(check_auto_saving_time(config_file_path, rules))
        except Exception:
            return 0.0

    def __call__(self, config_file_path: str, minutes: int) -> float:
        return self.forward(config_file_path, minutes)

    def to_code_prompt(self) -> str:
        return (
            "def check_auto_saving_time(config_file_path: str, minutes: int) -> float:\n"
            "    '''Return 1.0 if LibreOffice AutoSaveTimeIntervall equals minutes, else 0.0.\n"
            "    Note: config_file_path must be a Host path (download with get_ppt_config_file if needed).'''\n"
        )
