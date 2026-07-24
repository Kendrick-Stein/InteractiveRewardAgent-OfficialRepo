from smolagents import Tool
from typing import Any, Dict, List
import ast

class GetGnomeFavoriteAppsTool(Tool):
    """Return the current GNOME favorite applications list from the VM.

    Zero-argument tool that fetches the GNOME Shell favorite apps via gsettings.
    Returns a structured dict with the parsed apps list and metadata.
    """

    name = "get_gnome_favorite_apps"
    description = (
        "Get the current GNOME favorite apps list from the VM using gsettings. "
        "Returns an object with the apps list and metadata."
    )
    inputs = {}
    output_type = "object"

    def __init__(self, env: Any):
        super().__init__()
        self.env = env

    def forward(self) -> Dict[str, Any]:
        return self.__call__()

    def __call__(self) -> Dict[str, Any]:
        """Fetch and parse GNOME favorites using gsettings.

        Returns:
            dict: {
              "apps": List[str],
              "source": "gsettings",
              "ok": bool,
              "error": Optional[str]
            }
        """
        try:
            # Run inside VM and capture stdout
            code = (
                "import subprocess\n"
                "try:\n"
                "    out = subprocess.check_output(['gsettings','get','org.gnome.shell','favorite-apps'], "
                "                                stderr=subprocess.STDOUT, text=True).strip()\n"
                "    print(out)\n"
                "except Exception as e:\n"
                "    print('ERROR: ' + str(e))\n"
            )
            res = self.env.controller.execute_python_command(code)
            output: str = (res or {}).get('output', '')

            if not output or output.startswith('ERROR:'):
                return {
                    "apps": [],
                    "source": "gsettings",
                    "ok": False,
                    "error": output or "Failed to run gsettings"
                }

            # gsettings returns a Python-like list string; use safe literal_eval
            try:
                apps: List[str] = ast.literal_eval(output)
                if not isinstance(apps, list):
                    raise ValueError("gsettings output is not a list")
            except Exception as e:
                return {
                    "apps": [],
                    "source": "gsettings",
                    "ok": False,
                    "error": f"Parse error: {e}"
                }

            return {
                "apps": apps,
                "source": "gsettings",
                "ok": True,
                "error": None,
            }
        except Exception as e:
            return {
                "apps": [],
                "source": "gsettings",
                "ok": False,
                "error": f"Exception: {e}",
            }

    def to_code_prompt(self) -> str:
        return (
            "def get_gnome_favorite_apps() -> dict:\n"
            "    '''Return GNOME favorite apps list from the VM.'''\n"
        )
