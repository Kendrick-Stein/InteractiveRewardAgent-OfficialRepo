from __future__ import annotations

import os
import json
import base64
import datetime
from typing import Any, Optional

from smolagents import Tool

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # handled at runtime


class ObserveCurrentStateTool(Tool):
    """
    Read-only observation tool that captures the current VM screenshot and captions it
    using DeerAPI (OpenAI-compatible) gpt-4o-mini.

    Behavior:
    - Captures a screenshot via env without changing state.
    - Saves to output_dir/obs_pic/obs_{N}.png (or ./obs_pic by default).
    - Sends the image to DeerAPI for captioning.
    - Returns a compact JSON string with screenshot_path, caption, model, timestamp.

    Notes:
    - This tool is intended for bootstrap observation and evidence collection.
    - It does NOT take any interactive actions; it is strictly read-only.
    """

    name = "observe_current_state"
    description = (
    "Read-only visual observation and query tool. "
    "Captures the current GUI screenshot without performing any interaction, "
    "and answers a user-provided question based on the visual content of the screenshot "
    "using an OpenAI-compatible vision-language model. "
    "The question should target task-relevant visual information, such as UI state, "
    "visible elements, layout, text, or progress indicators, to help assess or plan task completion conditions. "
    "Returns a JSON string containing the screenshot path, model response, model name, and timestamp. "
    "This tool is strictly observational and MUST NOT alter the environment state."
)
    inputs = {
        "question": {
            "description": "Question to guide captioning. REQUIRED. The question should be the information you want to know about the current state, or the goal of the GUI task, or what's relevant to the task.",
            "type": "string",
        }
    }
    output_type = "string"

    def __init__(self, env: Any, model: str = "gpt-4o-mini"):
        self.env = env
        self.model = model
        self.output_dir: Optional[str] = None
        self.obs_pic_dir: Optional[str] = None
        self.obs_counter: int = 1
        super().__init__()

    def set_output_dir(self, output_dir: str):
        self.output_dir = output_dir
        self.obs_pic_dir = os.path.join(output_dir, "obs_pic")
        os.makedirs(self.obs_pic_dir, exist_ok=True)

    def _ensure_dirs(self):
        if not self.obs_pic_dir:
            # default to cwd/obs_pic when not set
            self.set_output_dir(os.getcwd())

    def forward(self, question: str) -> str:
        return self.__call__(question)

    def __call__(self, question: str) -> str:
        self._ensure_dirs()

        # Required parameter validation
        if not isinstance(question, str) or not question.strip():
            return json.dumps({"error": "question is required and must be a non-empty string"})

        # 1) Capture screenshot (read-only)
        try:
            obs = self.env._get_obs() if hasattr(self.env, "_get_obs") else {"screenshot": self.env.controller.get_screenshot()}
            screenshot_bytes = obs["screenshot"]
        except Exception as e:
            return json.dumps({"error": f"Failed to capture screenshot: {e}"})

        # 2) Save to disk
        img_path = os.path.join(self.obs_pic_dir, f"obs_{self.obs_counter:04d}.png")
        try:
            with open(img_path, "wb") as f:
                f.write(screenshot_bytes)
        except Exception as e:
            return json.dumps({"error": f"Failed to save screenshot: {e}"})

        # 3) Prepare captioning request (DeerAPI OpenAI-compatible)
        deer_key = os.getenv("IRA_API_KEY") or os.getenv("deerapi_key") or os.getenv("DEER_API_KEY")
        if not deer_key:
            # Do not fail hard; return minimal info
            payload = {
                "screenshot_path": img_path,
                "caption": "",
                "model": self.model,
                "timestamp": datetime.datetime.now().isoformat(),
                "warning": "Missing IRA_API_KEY (or legacy deerapi_key); skipping caption."
            }
            self.obs_counter += 1
            return json.dumps(payload)

        if OpenAI is None:
            payload = {
                "screenshot_path": img_path,
                "caption": "",
                "model": self.model,
                "timestamp": datetime.datetime.now().isoformat(),
                "warning": "openai python package not available; skipping caption."
            }
            self.obs_counter += 1
            return json.dumps(payload)

        try:
            base_url = os.getenv("IRA_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.cometapi.com/v1/"
            client = OpenAI(api_key=deer_key, base_url=base_url)

            # build base64 data URL from bytes (PNG)
            encoded_img = base64.b64encode(screenshot_bytes).decode("utf-8")
            base64_url = f"data:image/png;base64,{encoded_img}"

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": base64_url}},
                    ],
                }
            ]

            response = client.chat.completions.create(model=self.model, messages=messages)
            caption_text = response.choices[0].message.content
        except Exception as e:
            caption_text = f"Captioning failed: {e}"

        payload = {
            "screenshot_path": img_path,
            "caption": caption_text,
            "model": self.model,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        self.obs_counter += 1
        return json.dumps(payload)

    def to_code_prompt(self) -> str:
        return (
            "def observe_current_state(question: str) -> str:\n"
            "    \"\"\"Capture a read-only screenshot and caption it via DeerAPI. Returns a JSON string.\"\"\"\n"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test ObserveCurrentStateTool")
    parser.add_argument("--question", required=True, help="Question for captioning (REQUIRED)")
    args = parser.parse_args()

    # Minimal runtime test requires an env; here we only validate instantiation.
    print("ObserveCurrentStateTool ready (requires env in RewardAgent context)")
