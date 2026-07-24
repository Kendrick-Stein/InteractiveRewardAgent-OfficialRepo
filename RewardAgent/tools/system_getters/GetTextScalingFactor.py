from smolagents import Tool
from typing import Any, Dict

class GetTextScalingFactorTool(Tool):
    """Return the GNOME text scaling factor from the VM.

    Zero-argument tool that fetches the text-scaling-factor via gsettings.
    Returns a structured dict with the parsed float value and metadata.
    """

    name = "get_text_scaling_factor"
    description = (
        "Get the current GNOME text-scaling-factor via gsettings. Returns scaling_factor (float), "
        "source, ok and error fields."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, env: Any):
        super().__init__()
        self.env = env

    def forward(self) -> Dict[str, Any]:
        return self.__call__()

    def __call__(self) -> Dict[str, Any]:
        try:
            code = (
                "import subprocess\n"
                "try:\n"
                "    out = subprocess.check_output(['gsettings','get','org.gnome.desktop.interface','text-scaling-factor'], "
                "                                stderr=subprocess.STDOUT, text=True).strip()\n"
                "    print(out)\n"
                "except Exception as e:\n"
                "    print('ERROR: ' + str(e))\n"
            )
            res = self.env.controller.execute_python_command(code)
            output: str = (res or {}).get('output', '')

            if not output or output.startswith('ERROR:'):
                return {
                    "scaling_factor": None,
                    "source": "gsettings",
                    "ok": False,
                    "error": output or "Failed to run gsettings"
                }
            try:
                # gsettings returns number like '1.25' or sometimes '1'
                val = float(output)
            except Exception as e:
                return {
                    "scaling_factor": None,
                    "source": "gsettings",
                    "ok": False,
                    "error": f"Parse error: {e}"
                }

            return {
                "scaling_factor": val,
                "source": "gsettings",
                "ok": True,
                "error": None,
            }
        except Exception as e:
            return {
                "scaling_factor": None,
                "source": "gsettings",
                "ok": False,
                "error": f"Exception: {e}",
            }

    def to_code_prompt(self) -> str:
        return (
            "def get_text_scaling_factor() -> dict:\n"
            "    '''Return GNOME text scaling factor (float) from the VM.'''\n"
        )
