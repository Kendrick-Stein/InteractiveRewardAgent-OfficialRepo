from smolagents import Tool
from typing import Any, Dict
import re

class GetSystemUtcOffsetTool(Tool):
    """Return the system's current UTC offset from the VM.

    Zero-argument tool that tries timedatectl first, then falls back to `date +%z`.
    Returns a structured dict with offset string and derived hours/minutes.
    """

    name = "get_system_utc_offset"
    description = (
        "Get the system's current UTC offset from the VM. Tries timedatectl and falls back to date +%z. "
        "Returns offset_string (+/-HHMM), offset_hours (float), offset_minutes (int), source, ok, error."
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
            # First attempt: timedatectl status
            code_tdc = (
                "import subprocess\n"
                "try:\n"
                "    out = subprocess.check_output(['timedatectl','status'], stderr=subprocess.STDOUT, text=True)\n"
                "    print(out)\n"
                "except Exception as e:\n"
                "    print('ERROR: ' + str(e))\n"
            )
            res_tdc = self.env.controller.execute_python_command(code_tdc)
            output_tdc: str = (res_tdc or {}).get('output', '')

            offset = None
            source = None

            if output_tdc and not output_tdc.startswith('ERROR:'):
                # Try to find an offset like +0800 or -0530 in the timedatectl output
                # Prefer one on the 'Time zone:' line if present
                tz_line = None
                for line in output_tdc.splitlines():
                    if line.strip().startswith('Time zone:'):
                        tz_line = line
                        break
                search_target = tz_line or output_tdc
                m = re.search(r"([+-]\d{4})", search_target)
                if m:
                    offset = m.group(1)
                    source = 'timedatectl'

            # Fallback to date +%z if timedatectl failed or no offset found
            if offset is None:
                code_date = (
                    "import subprocess\n"
                    "try:\n"
                    "    out = subprocess.check_output(['date','+%z'], stderr=subprocess.STDOUT, text=True).strip()\n"
                    "    print(out)\n"
                    "except Exception as e:\n"
                    "    print('ERROR: ' + str(e))\n"
                )
                res_date = self.env.controller.execute_python_command(code_date)
                output_date: str = (res_date or {}).get('output', '')
                if output_date and not output_date.startswith('ERROR:') and re.match(r"^[+-]\d{4}$", output_date):
                    offset = output_date
                    source = 'date'

            if offset is None:
                return {
                    "offset_string": None,
                    "offset_hours": None,
                    "offset_minutes": None,
                    "source": source or 'timedatectl/date',
                    "ok": False,
                    "error": "Could not determine UTC offset"
                }

            # Compute minutes and hours
            sign = -1 if offset.startswith('-') else 1
            hh = int(offset[1:3])
            mm = int(offset[3:5])
            total_minutes = sign * (hh * 60 + mm)
            offset_hours = round(total_minutes / 60.0, 2)

            return {
                "offset_string": offset,
                "offset_hours": offset_hours,
                "offset_minutes": total_minutes,
                "source": source,
                "ok": True,
                "error": None,
            }
        except Exception as e:
            return {
                "offset_string": None,
                "offset_hours": None,
                "offset_minutes": None,
                "source": 'timedatectl/date',
                "ok": False,
                "error": f"Exception: {e}",
            }

    def to_code_prompt(self) -> str:
        return (
            "def get_system_utc_offset() -> dict:\n"
            "    '''Return the system UTC offset (+/-HHMM) with derived hours/minutes.'''\n"
        )
