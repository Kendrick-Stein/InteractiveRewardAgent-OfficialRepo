from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from smolagents import Tool


class ContainsPageBreakTool(Tool):
    name = "contains_page_break"
    description = (
        "Check whether a DOCX file contains page breaks. "
        "Optionally validate the expected page break count. "
        "IMPORTANT: file_path must be a Host path. If your file is inside the VM (e.g., /home/user/...), "
        "use get_vm_file(vm_path, dest_name) to download it to Host first and pass the returned Host path."
    )
    inputs = {
        "file_path": {
            "description": "Path to the .docx file on the Host (absolute or relative).",
            "type": "string",
        },
        "expected_page_break_count": {
            "description": "Optional expected count of page breaks to match.",
            "type": "integer",
        },
    }
    output_type = "string"

    def forward(self, file_path: str, expected_page_break_count: int ) -> str:
        return self.__call__(file_path, expected_page_break_count)

    def __call__(self, file_path: str, expected_page_break_count: int) -> str:
        try:
            if not file_path:
                return json.dumps({"passed": False, "details": "file_path is required"}, ensure_ascii=False)
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path):
                return json.dumps({
                    "passed": False,
                    "details": (
                        f"File not found on host: {abs_path}. If your file is in the VM, use get_vm_file to download it first."
                    )
                }, ensure_ascii=False)

            try:
                from docx import Document
            except Exception as e:
                return json.dumps({"passed": False, "details": f"python-docx import error: {e}"}, ensure_ascii=False)

            try:
                doc = Document(abs_path)
            except Exception as e:
                return json.dumps({"passed": False, "details": f"Failed to open DOCX: {e}"}, ensure_ascii=False)

            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            page_break_count = 0
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    br_elems = run.element.findall('.//w:br', namespaces)
                    for br in br_elems:
                        if br is not None and '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type' in br.attrib and \
                                br.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type'] == 'page':
                            page_break_count += 1

            if expected_page_break_count is not None and page_break_count != int(expected_page_break_count):
                return json.dumps({
                    "passed": False,
                    "details": f"Page break count mismatch: expected {expected_page_break_count}, found {page_break_count}"
                }, ensure_ascii=False)

            passed = page_break_count > 0
            return json.dumps({
                "passed": passed,
                "details": "Page breaks present" if passed else "No page breaks found"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"passed": False, "details": f"Error: {e}"}, ensure_ascii=False)

    def to_code_prompt(self) -> str:
        return (
            "def contains_page_break(file_path: str, expected_page_break_count: int | None = None) -> str:\n"
            "    '''Check whether a DOCX file contains page breaks; optionally validate expected count.\n"
            "    file_path must be a Host path; if the file is in the VM, first use get_vm_file.\n"
            "    Returns a JSON string with keys passed (bool) and details (str).'''\n"
        )
