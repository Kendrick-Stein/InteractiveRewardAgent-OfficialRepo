from __future__ import annotations

import json
import os

from smolagents import Tool


class DocxItalicFontSize14Tool(Tool):
    name = "docx_italic_font_size_14"
    description = (
        "Verify that all italic runs in the DOCX have font size 14pt. "
        "This is a single-file adaptation of check_italic_font_size_14. "
        "IMPORTANT: file_path must be a Host path. If your file is inside the VM (e.g., /home/user/...), "
        "use get_vm_file(vm_path, dest_name) to download it to Host first and pass the returned Host path."
    )
    inputs = {
        "file_path": {
            "description": "Path to the .docx file on the Host (absolute or relative).",
            "type": "string",
        }
    }
    output_type = "string"

    def forward(self, file_path: str) -> str:
        return self.__call__(file_path)

    def __call__(self, file_path: str) -> str:
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
                document = Document(abs_path)
            except Exception as e:
                return json.dumps({"passed": False, "details": f"Failed to open DOCX: {e}"}, ensure_ascii=False)

            for paragraph in document.paragraphs:
                for run in paragraph.runs:
                    if run.italic:
                        # Font size must be explicitly 14pt
                        if run.font.size is None or getattr(run.font.size, 'pt', None) != 14:
                            return json.dumps({
                                "passed": False,
                                "details": "Found italic text not set to 14pt"
                            }, ensure_ascii=False)

            return json.dumps({"passed": True, "details": "All italic text is 14pt"}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"passed": False, "details": f"Error: {e}"}, ensure_ascii=False)

    def to_code_prompt(self) -> str:
        return (
            "def docx_italic_font_size_14(file_path: str) -> str:\n"
            "    '''Verify that all italic runs in the DOCX have font size 14pt.\n"
            "    file_path must be a Host path; if the file is in the VM, first use get_vm_file.\n"
            "    Returns a JSON string with keys passed (bool) and details (str).'''\n"
        )
