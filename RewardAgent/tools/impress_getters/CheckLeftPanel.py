from smolagents import Tool
from desktop_env.evaluators.metrics.slides import check_left_panel


class CheckLeftPanelTool(Tool):
    name = "check_left_panel"
    description = (
        "Check whether the Slides View (left panel) is open based on an accessibility tree XML string. "
        "Input must be the Host-side XML text captured from the environment. Returns 1 if open, else 0."
    )
    inputs = {
        "accessibility_tree_xml": {
            "type": "string",
            "description": (
                "AT-SPI-like accessibility tree XML string from the Host. "
                "Do not pass VM paths; provide the XML content as a string."
            ),
        },
    }
    output_type = "number"

    def forward(self, accessibility_tree_xml: str) -> float:
        try:
            return float(check_left_panel(accessibility_tree_xml))
        except Exception:
            return 0.0

    def __call__(self, accessibility_tree_xml: str) -> float:
        return self.forward(accessibility_tree_xml)

    def to_code_prompt(self) -> str:
        return (
            "def check_left_panel(accessibility_tree_xml: str) -> float:\n"
            "    '''Return 1.0 if 'Slides View' document-frame is present (left panel open), else 0.0.\n"
            "    Note: accessibility_tree_xml must be the Host-side XML string.'''\n"
        )
