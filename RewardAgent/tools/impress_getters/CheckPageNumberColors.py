from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_page_number_colors


class CheckPageNumberColorsTool(Tool):
    name = "check_page_number_colors"
    description = (
        "Check that page/slide number color in the PPTX slide master matches the expected color. "
        "Accepts a Host path to the .pptx file and a color string among: red, blue, green, black. "
        "Returns 1 if matched, else 0."
    )
    inputs = {
        "pptx_file_path": {
            "type": "string",
            "description": (
                "Host path to the .pptx file. Do not pass VM paths; use get_vm_file first if needed to copy to Host."
            ),
        },
        "color": {
            "type": "string",
            "description": "Expected color name: 'red' | 'blue' | 'green' | 'black'",
        },
    }
    output_type = "number"

    def forward(self, pptx_file_path: str, color: str) -> float:
        try:
            rules = {"color": str(color).lower()}
            return float(check_page_number_colors(pptx_file_path, rules))
        except Exception:
            return 0.0

    def __call__(self, pptx_file_path: str, color: str) -> float:
        return self.forward(pptx_file_path, color)

    def to_code_prompt(self) -> str:
        return (
            "def check_page_number_colors(pptx_file_path: str, color: str) -> float:\n"
            "    '''Return 1.0 if slide number color matches given color (red|blue|green|black), else 0.0.\n"
            "    Note: pptx_file_path must be a Host path.'''\n"
        )
