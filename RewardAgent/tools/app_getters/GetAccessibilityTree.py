from smolagents import Tool
from desktop_env.evaluators.getters.misc import get_accessibility_tree
import re


def optimize_accessibility_xml(xml_content: str) -> str:
    """
    Optimize accessibility tree XML by removing redundant attributes.

    Optimization strategy (saves ~58% size):
    1. Remove empty action attributes (act:*_desc="", act:*_kb="")
    2. Remove default true values (st:visible="true", st:enabled="true", st:sensitive="true")
    3. Remove all act:* attributes (action descriptions, usually empty or redundant)

    Args:
        xml_content: Original XML string

    Returns:
        Optimized XML string (smaller, ~58% reduction)
    """
    if not xml_content or len(xml_content) < 1000:
        return xml_content

    original_len = len(xml_content)

    # 1. Remove all act:* attributes (action descriptions, keyboard shortcuts)
    # Pattern: act:xxx="yyy" (including empty values)
    xml_content = re.sub(r'\s+act:[a-zA-Z_]+=\"[^\"]*\"', '', xml_content)

    # 2. Remove default true values for state attributes
    # These are typically the default and can be omitted
    default_true_attrs = [
        'st:visible',
        'st:enabled',
        'st:sensitive',
        'st:focusable',
        'st:showing',
        'st:selectable_text',
    ]
    for attr in default_true_attrs:
        xml_content = re.sub(rf'\s+{attr}=\"true\"', '', xml_content)

    # 3. Remove empty attributes (any attribute with empty value)
    xml_content = re.sub(r'\s+[a-zA-Z_]+:[a-zA-Z_]+=\"\"', '', xml_content)

    # 4. Remove redundant xmlns declarations (keep only at root)
    # Find xmlns in non-root elements and remove them
    # This is tricky, so we'll just remove xmlns from closing tags context

    # Clean up any extra whitespace left by removals
    xml_content = re.sub(r'\s+>', '>', xml_content)
    xml_content = re.sub(r'\s+\s+', ' ', xml_content)

    optimized_len = len(xml_content)
    reduction = (original_len - optimized_len) / original_len * 100

    if reduction > 10:
        # Only log if significant reduction
        print(f"[GetAccessibilityTree] Optimized XML: {original_len} -> {optimized_len} chars ({reduction:.1f}% reduction)")

    return xml_content


class GetAccessibilityTreeTool(Tool):
    name = "get_accessibility_tree"
    description = (
        "Fetch the current Accessibility Tree (A11y) XML from the active desktop environment.\n\n"
        "This returns an optimized XML string (reduced ~58% by removing redundant attributes).\n"
        "The optimization removes: empty action attributes, default true state values, and action descriptions.\n"
        "You can parse it using lxml with the provided namespaces."
    )
    inputs = {}
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self) -> str:
        try:
            at_xml: str = get_accessibility_tree(self.env)
            if at_xml is None:
                return ""

            # Optimize the XML to reduce token usage
            optimized_xml = optimize_accessibility_xml(at_xml)
            return optimized_xml
        except Exception as e:
            return f"Error: Failed to get accessibility tree: {str(e)}"

    def __call__(self) -> str:
        return self.forward()

    def to_code_prompt(self) -> str:
        return (
            "Use get_accessibility_tree() to retrieve the desktop Accessibility Tree (XML).\n"
            "Example:\n"
            "- xml_str = get_accessibility_tree()\n\n"
            "Notes:\n"
            "- Output is an optimized XML string (~58% smaller than raw output).\n"
            "- Namespace map differs by OS but is provided inside the XML's nsmap.\n"
        )
