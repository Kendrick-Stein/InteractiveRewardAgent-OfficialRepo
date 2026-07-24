from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_transition


class CheckTransitionTool(Tool):
    name = "check_transition"
    description = (
        "Check whether a specific slide has the expected transition type. "
        "Accepts a Host path to the .pptx file, slide index (0-based), and transition type string (e.g., 'dissolve'). "
        "Returns 1 if matched, else 0."
    )
    inputs = {
        "pptx_file_path": {
            "type": "string",
            "description": (
                "Host path to the .pptx file. Do not pass VM paths; use get_vm_file first if needed to copy to Host."
            ),
        },
        "slide_idx": {
            "type": "integer",
            "description": "0-based slide index to check",
        },
        "transition_type": {
            "type": "string",
            "description": "Expected transition element name (e.g., 'dissolve', 'fade')",
        },
    }
    output_type = "number"

    def forward(self, pptx_file_path: str, slide_idx: int, transition_type: str) -> float:
        try:
            rules = {"slide_idx": int(slide_idx), "transition_type": str(transition_type)}
            return float(check_transition(pptx_file_path, rules))
        except Exception:
            return 0.0

    def __call__(self, pptx_file_path: str, slide_idx: int, transition_type: str) -> float:
        return self.forward(pptx_file_path, slide_idx, transition_type)

    def to_code_prompt(self) -> str:
        return (
            "def check_transition(pptx_file_path: str, slide_idx: int, transition_type: str) -> float:\n"
            "    '''Return 1.0 if the slide has the given transition type, else 0.0.\n"
            "    Note: pptx_file_path must be a Host path.'''\n"
        )
