from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_slide_orientation_Portrait


class CheckSlideOrientationPortraitTool(Tool):
    name = "check_slide_orientation_portrait"
    description = (
        "Check whether the PPTX slide size is portrait (height > width). "
        "Accepts a Host path to the .pptx file. Returns 1 if portrait, else 0."
    )
    inputs = {
        "pptx_file_path": {
            "type": "string",
            "description": (
                "Host path to the .pptx file. Do not pass VM paths; use get_vm_file first if needed to copy to Host."
            ),
        },
    }
    output_type = "number"

    def forward(self, pptx_file_path: str) -> float:
        try:
            return float(check_slide_orientation_Portrait(pptx_file_path))
        except Exception:
            return 0.0

    def __call__(self, pptx_file_path: str) -> float:
        return self.forward(pptx_file_path)

    def to_code_prompt(self) -> str:
        return (
            "def check_slide_orientation_portrait(pptx_file_path: str) -> float:\n"
            "    '''Return 1.0 if slide size is portrait (height > width), else 0.0.\n"
            "    Note: pptx_file_path must be a Host path.'''\n"
        )
