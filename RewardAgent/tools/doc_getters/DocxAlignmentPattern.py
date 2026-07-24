from __future__ import annotations

import json
import os
import re
from typing import List

from smolagents import Tool
from docx import Document


def _alignment_sentence_ok(sentence: str) -> bool:
    """
    For a given sentence string, verify that if it has >= 3 words, the first
    3 words are separated from the rest by a large space (>=3 spaces) or a tab.
    We check the immediate whitespace after the 3rd word.
    Sentences with < 3 words are considered not applicable and thus OK.
    """
    s = sentence.strip()
    if not s:
        return True

    # Find word spans using regex for word characters
    word_spans = list(re.finditer(r"\b\w+\b", s))
    if len(word_spans) < 3:
        return True  # Not applicable

    third_end = word_spans[2].end()
    rest = s[third_end:]

    # Measure leading whitespace immediately following the 3rd word
    m = re.match(r"^(\s+)", rest)
    if not m:
        return False
    ws = m.group(1)

    # Condition: a tab OR at least 3 spaces
    if "\t" in ws:
        return True
    if ws.count(" ") >= 3:
        return True
    return False


class DocxAlignmentPatternTool(Tool):
    name = "docx_alignment_pattern"
    description = (
        "Validate sentence alignment pattern: the first three words should be separated from the rest by a large space/tab in each sentence across paragraphs. "
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

            doc = Document(abs_path)
            checked = 0
            failed_examples: List[str] = []

            for p in doc.paragraphs:
                text = p.text or ""
                # Split into sentences by '.' while preserving basic structure
                sentences = [s for s in re.split(r"\.+", text) if s.strip()]
                for s in sentences:
                    # Only consider sentences with >= 3 words
                    if len(re.findall(r"\b\w+\b", s)) >= 3:
                        checked += 1
                        if not _alignment_sentence_ok(s):
                            if len(failed_examples) < 5:
                                failed_examples.append(s.strip()[:80])

            if checked == 0:
                return json.dumps({
                    "passed": False,
                    "details": "No sentences with >=3 words found to validate alignment pattern"
                }, ensure_ascii=False)

            if failed_examples:
                return json.dumps({
                    "passed": False,
                    "details": f"Alignment pattern not satisfied for some sentences. Examples: {failed_examples}"
                }, ensure_ascii=False)

            return json.dumps({
                "passed": True,
                "details": f"Alignment pattern satisfied across {checked} sentences with >=3 words"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"passed": False, "details": f"Error: {e}"}, ensure_ascii=False)

    def to_code_prompt(self) -> str:
        return (
            "def docx_alignment_pattern(file_path: str) -> str:\n"
            "    '''Validate sentence alignment pattern: first three words separated from the rest by a large space/tab.\n"
            "    file_path must be a Host path; if the file is in the VM, first use get_vm_file.\n"
            "    Returns a JSON string with keys passed (bool) and details (str).'''\n"
        )
