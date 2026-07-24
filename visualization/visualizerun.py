import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Threshold (characters) above which long text/code will be collapsed with <details>
COLLAPSE_THRESHOLD = 800


def _escape_html(s: Any) -> str:
    """Safe HTML escape for arbitrary values."""
    import html
    try:
        return html.escape(str(s), quote=True)
    except Exception:
        return html.escape(repr(s), quote=True)


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt_timing(timing: Optional[Dict[str, Any]]) -> str:
    if not isinstance(timing, dict):
        return ""
    dur = timing.get("duration")
    start = timing.get("start_time")
    end = timing.get("end_time")
    parts: List[str] = []
    if start is not None:
        parts.append(f"start: {start}")
    if end is not None:
        parts.append(f"end: {end}")
    if dur is not None:
        parts.append(f"duration: {dur:.3f}s" if isinstance(dur, (int, float)) else f"duration: {dur}")
    return " | ".join(parts)


def _block(title: str, body_html: str, extra_class: str = "", anchor: Optional[str] = None) -> str:
    anchor_attr = f" id=\"{_escape_html(anchor)}\"" if anchor else ""
    return f"""
    <section class=\"card {extra_class}\"{anchor_attr}>
      <h2 class=\"card-title\">{_escape_html(title)}</h2>
      <div class=\"card-body\">{body_html}</div>
    </section>
    """


def _code_block(content: Any) -> str:
    # Render arbitrary content as a preformatted code block (escaped).
    text = str(content) if content is not None else ""
    return f"<pre class=\"code\">{_escape_html(text)}</pre>"


def _kv_table(rows: List[Tuple[str, Any]]) -> str:
    items = []
    for k, v in rows:
        items.append(
            f"<tr><th>{_escape_html(k)}</th><td>{_escape_html(v)}</td></tr>"
        )
    return f"<table class=\"kv\">{''.join(items)}</table>"


def _collapse_if_long(inner_html: str, label: str, raw_text: str, threshold: int = COLLAPSE_THRESHOLD) -> str:
    """Wrap inner_html with a <details> collapsible when raw_text is long."""
    try:
        length = len(raw_text or "")
    except Exception:
        length = threshold  # if unknown, force collapse
    if length <= threshold:
        return inner_html
    summary = _escape_html(f"{label} · expand/collapse · {length} chars")
    return f"""
    <details class=\"collapsible\">
      <summary>{summary}</summary>
      <div class=\"collapsible-body\">{inner_html}</div>
    </details>
    """


# ---------- Chat rendering helpers ----------

def _content_to_text(content: Any) -> str:
    """Normalize message content to a plain string.
    Supports smolagents formats where content can be a string or a list of {type,text}.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for it in content:
            if isinstance(it, dict):
                t = it.get("type")
                if t == "text":
                    parts.append(str(it.get("text", "")))
                else:
                    # Unknown types -> best effort stringify
                    parts.append(str(it))
            else:
                parts.append(str(it))
        return "\n\n".join(parts)
    # Unknown structure
    return str(content)


def _split_code_blocks(raw: str) -> List[Tuple[str, str]]:
    """Split raw text into [('text'|'code'|'thoughts', value), ...].
    - Extract a leading "Thoughts:" section if present
    - Parse literal <code> ... </code> blocks from the remaining text
    """
    out: List[Tuple[str, str]] = []
    text = raw or ""

    # Extract Thoughts: ... (until first <code> or end)
    thoughts_idx = text.find("Thoughts:")
    if thoughts_idx != -1:
        # Grab from 'Thoughts:' to either first <code> or end
        code_open_idx = text.find("<code>")
        end_idx = code_open_idx if code_open_idx != -1 else len(text)
        thoughts_chunk = text[thoughts_idx:end_idx].strip()
        if thoughts_chunk:
            out.append(("thoughts", thoughts_chunk))
        # Remove that segment from text so it won't be duplicated in text parts
        if end_idx <= len(text):
            text = (text[:thoughts_idx] + text[end_idx:]).strip()

    # Now parse <code>...</code> pairs
    cur = text
    while True:
        open_i = cur.find("<code>")
        if open_i == -1:
            if cur.strip():
                out.append(("text", cur.strip()))
            break
        # Any leading text
        lead = cur[:open_i]
        if lead.strip():
            out.append(("text", lead.strip()))
        after_open = cur[open_i + len("<code>") :]
        close_i = after_open.find("</code>")
        if close_i == -1:
            # No closing tag; treat remainder as text
            if after_open.strip():
                out.append(("text", after_open.strip()))
            break
        code_block = after_open[:close_i]
        out.append(("code", code_block.strip()))
        cur = after_open[close_i + len("</code>") :]

    return out


def _render_chat_messages(messages: List[Dict[str, Any]]) -> str:
    """Render messages into chat bubbles grouped by role.
    Roles: user (left), assistant (right), system (center), tool-call, tool-response
    Each message may contain Thoughts section and <code> blocks.
    """
    if not isinstance(messages, list) or not messages:
        return "<p class=\"muted\">(No conversation messages)</p>"

    def role_to_class_and_label(role_raw: str) -> Tuple[str, str]:
        r = (role_raw or "").lower()
        if r in ("user",):
            return "user", "User"
        if r in ("system",):
            return "system", "System"
        if r in ("tool-call", "tool_call", "toolcall"):
            return "toolcall", "Tool Call"
        if r in ("tool-response", "tool_response", "toolresponse"):
            return "toolresp", "Tool Response"
        # default
        return "assistant", "Assistant"

    html_parts: List[str] = ["<div class=\"chat\">"]
    for i, m in enumerate(messages, start=1):
        role_class, label = role_to_class_and_label(m.get("role") or "")
        content_raw = _content_to_text(m.get("content"))
        parts = _split_code_blocks(content_raw)

        # Build the bubble body
        body_chunks: List[str] = []
        for kind, val in parts:
            if kind == "thoughts":
                body_chunks.append(
                    f"<div class=\"thoughts\"><div class=\"thoughts-title\">Thoughts</div><div class=\"thoughts-body\">{_escape_html(val)}</div></div>"
                )
            elif kind == "code":
                code_html = _code_block(val)
                body_chunks.append(_collapse_if_long(code_html, "Code block", val))
            else:
                # Convert text to paragraphs, keep newlines
                safe = _escape_html(val)
                safe_html = safe.replace("\n", "<br/>")
                text_html = f"<div class=\"msg-text\">{safe_html}</div>"
                body_chunks.append(_collapse_if_long(text_html, "Long message", val))

        bubble = f"""
        <div class=\"msg {role_class}\">
          <div class=\"header\">{_escape_html(label)} <span class=\"idx\">#{i}</span></div>
          <div class=\"bubble\">{''.join(body_chunks)}</div>
        </div>
        """
        html_parts.append(bubble)

    html_parts.append("</div>")
    return "".join(html_parts)


# ---------- Steps rendering ----------

def _render_steps(steps: List[Dict[str, Any]], include_timeline: bool = False) -> Tuple[str, str]:
    """
    Returns (final_step_html, all_steps_html)
    - final step is rendered as chat bubbles if it contains model_input_messages
    - all steps are rendered as a timeline using generic renderer
    """
    if not steps:
        return ("<p>No steps available.</p>", "<p>No steps available.</p>")

    # Prefer messages in the last step; else fall back to last step that has messages
    def find_messages() -> Optional[List[Dict[str, Any]]]:
        if isinstance(steps[-1].get("model_input_messages"), list) and steps[-1]["model_input_messages"]:
            return steps[-1]["model_input_messages"]
        for st in reversed(steps):
            msgs = st.get("model_input_messages")
            if isinstance(msgs, list) and msgs:
                return msgs
        return None

    messages = find_messages()

    # Augment final chat with model_output_message or observations/action_output if missing
    try:
        last_step = steps[-1]
        augmented = list(messages) if messages else []
        # helper to check presence of a role+content match
        def _has_content(role: str, content_text: str) -> bool:
            for mm in augmented:
                if (mm.get("role") or "").lower() == role.lower():
                    # content may be str or list; normalize
                    existing = _content_to_text(mm.get("content"))
                    if existing.strip() == str(content_text or "").strip():
                        return True
            return False

        # Append final assistant message from model_output_message if exists and not present
        mo = last_step.get("model_output_message")
        mo_content = None
        if isinstance(mo, dict):
            mo_content = mo.get("content")
        else:
            mo_content = last_step.get("model_output") or last_step.get("model_output_message")
        if isinstance(mo_content, (str, list)) and not _has_content("assistant", _content_to_text(mo_content)):
            augmented.append({"role": "assistant", "content": mo_content})

        # Append observations as tool-response if not already present
        obs = last_step.get("observations")
        if obs is not None and not _has_content("tool-response", f"Observation:\n{obs if isinstance(obs, str) else json.dumps(obs, ensure_ascii=False)}"):
            obs_text = obs if isinstance(obs, str) else json.dumps(obs, ensure_ascii=False, indent=2)
            augmented.append({"role": "tool-response", "content": f"Observation:\n{obs_text}"})

        # Append action_output as tool-response if not present
        ao = last_step.get("action_output")
        if ao is not None and not _has_content("tool-response", _content_to_text(ao)):
            ao_text = ao if isinstance(ao, str) else json.dumps(ao, ensure_ascii=False, indent=2)
            augmented.append({"role": "tool-response", "content": ao_text})

        # Use augmented messages if we added anything
        if augmented and (not messages or len(augmented) != len(messages)):
            messages = augmented
    except Exception:
        # fall back silently
        pass

    def render_one(step: Dict[str, Any], index: int) -> str:
        title_parts = []
        sn = step.get("step_number")
        if sn is not None:
            title_parts.append(f"Step {sn}")
        else:
            title_parts.append(f"Item {index+1}")
        timing_html = _fmt_timing(step.get("timing"))
        if timing_html:
            title_parts.append(f"({timing_html})")
        title = " ".join(title_parts)

        task_text = step.get("task")
        model_input = step.get("model_input_messages")
        model_output = step.get("model_output_message", {}).get("content") if isinstance(step.get("model_output_message"), dict) else step.get("model_output") or step.get("model_output_message")
        tool_calls = step.get("tool_calls")
        observations = step.get("observations")
        action_output = step.get("action_output")
        code_action = step.get("code_action")

        body_parts: List[str] = []
        if task_text:
            body_parts.append(f"<h4>Task</h4>" + _collapse_if_long(_code_block(task_text), "Task", str(task_text)))
        if model_input:
            mi_str = json.dumps(model_input, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Model Input (Raw)</h4>" + _collapse_if_long(_code_block(mi_str), "Model Input", mi_str))
        if model_output:
            mo_str = model_output if isinstance(model_output, str) else json.dumps(model_output, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Model Output</h4>" + _collapse_if_long(_code_block(mo_str), "Model Output", mo_str))
        if code_action:
            ca_str = code_action if isinstance(code_action, str) else json.dumps(code_action, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Code Action</h4>" + _collapse_if_long(_code_block(ca_str), "Code Action", ca_str))
        if tool_calls:
            tc_str = json.dumps(tool_calls, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Tool Calls</h4>" + _collapse_if_long(_code_block(tc_str), "Tool Calls", tc_str))
        if observations:
            ob_str = observations if isinstance(observations, str) else json.dumps(observations, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Observations</h4>" + _collapse_if_long(_code_block(ob_str), "Observations", ob_str))
        if action_output is not None:
            ao_str = action_output if isinstance(action_output, str) else json.dumps(action_output, ensure_ascii=False, indent=2)
            body_parts.append("<h4>Action Output</h4>" + _collapse_if_long(_code_block(ao_str), "Action Output", ao_str))

        if not body_parts:
            body_parts.append("<p class=\"muted\">(No content)</p>")

        return _block(title, "".join(body_parts), extra_class="step")

    # Final step UI
    if messages:
        final_html = _block(
            "Final Conversation (includes full message history)",
            _render_chat_messages(messages),
            extra_class="final-step",
            anchor="final-chat"
        )
    else:
        final_html = _block(
            "Final Step (includes full message history)",
            render_one(steps[-1], len(steps) - 1),
            extra_class="final-step",
            anchor="final-chat"
        )

    if include_timeline:
        timeline_items = [render_one(s, i) for i, s in enumerate(steps)]
        timeline_html = "".join(timeline_items)
    else:
        timeline_html = ""

    return final_html, timeline_html


def _build_html(doc: Dict[str, Any], source_path: str, include_timeline: bool = False) -> str:
    meta = doc.get("meta", {}) or {}
    evaluation = doc.get("evaluation", {}) or {}
    final_output = doc.get("final_output", "")
    full_code = doc.get("full_code", "")
    steps: List[Dict[str, Any]] = doc.get("steps", []) or []

    # Header info
    title = "Smolagent Run Report"
    task_instruction = meta.get("task_instruction", "")
    timestamp = meta.get("timestamp") or datetime.now().isoformat()
    agent_class = meta.get("agent_class")
    model_id = meta.get("model_id")
    max_steps = meta.get("max_steps")

    verdict = evaluation.get("verdict", "") or "-"
    reward = evaluation.get("reward", "")

    eval_rows = [
        ("Reward", evaluation.get("reward", "")),
        ("Verdict", verdict),
        ("Reasoning", evaluation.get("reasoning", "")),
    ]

    meta_rows = [
        ("Task Instruction", task_instruction),
        ("Model", model_id or ""),
        ("Agent", agent_class or ""),
        ("Max Steps", max_steps or ""),
        ("Timestamp", timestamp),
        ("Source JSON", source_path),
    ]

    final_step_html, timeline_html = _render_steps(steps, include_timeline=include_timeline)

    # verdict badge
    badge_cls = "badge-partial"
    if str(verdict).lower() == "success":
        badge_cls = "badge-success"
    elif str(verdict).lower() == "failure":
        badge_cls = "badge-failure"

    # top navigation
    if include_timeline:
        toc_html = """
          <nav class=\"toc\">
            <a href=\"#summary\">Summary</a>
            <a href=\"#final-chat\">Final Conversation</a>
            <a href=\"#timeline\">All Steps</a>
            <a href=\"#full-code\">Full Code</a>
            <a href=\"#meta\">Metadata</a>
          </nav>
        """
    else:
        toc_html = """
          <nav class=\"toc\">
            <a href=\"#summary\">Summary</a>
            <a href=\"#final-chat\">Final Conversation</a>
            <a href=\"#full-code\">Full Code</a>
            <a href=\"#meta\">Metadata</a>
          </nav>
        """

    # Precompute overview content to avoid backslashes inside f-string expressions
    overview_content_html = (
        f'<div><span class="badge {badge_cls}">Verdict: {_escape_html(verdict)}</span> '
        f'<span class="badge" style="margin-left:8px;">Reward: {_escape_html(reward)}</span></div>'
    )

    # Precompute optional timeline section
    timeline_section_html = ""
    if include_timeline and timeline_html:
        timeline_section_html = f"""
  <div class=\"page-break\"></div>
  {_block("All Steps Timeline", timeline_html, anchor="timeline")}
"""

    html = f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{_escape_html(title)}</title>
  <style>
    :root {{
      /* Dark theme */
      --bg: #0b0f14;
      --text: #e5eef7;
      --muted: #9fb2c8;
      --card: #121821;
      --panel: #0f1720;
      --border: #1f2a37;
      --accent: #3aa0ff;
      --ok: #22c55e;
      --warn: #f59e0b;
      --error: #ef4444;
      --code-bg: #0b1020;
      --code-text: #e5e7eb;
      --bubble-user: #0e2239; /* blue-ish */
      --bubble-assistant: #14321d; /* green-ish */
      --bubble-system: #1b2430; /* gray */
      --bubble-toolcall: #3a2a06; /* warm warn */
      --bubble-toolresp: #0a2332; /* cold accent */
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 24px; background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif; }}

    .header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }}
    .header .ts {{ color: var(--muted); font-size: 12px; }}

    .toc {{ display: flex; gap: 10px; flex-wrap: wrap; margin: 8px 0 16px; }}
    .toc a {{ color: #cde3ff; text-decoration: none; background: #0c1320; border: 1px solid var(--border); padding: 6px 10px; border-radius: 999px; font-size: 12px; }}
    .toc a:hover {{ background: #132032; }}

    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}

    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; margin-bottom: 16px; break-inside: avoid; }}
    .card-title {{ font-size: 16px; margin-bottom: 8px; }}
    .card-body {{ font-size: 13px; }}
    .final-step .card {{ border-color: var(--accent); box-shadow: 0 0 0 2px rgba(58,160,255,0.15) inset; }}

    table.kv {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    table.kv th {{ text-align: left; width: 160px; padding: 6px 8px; color: var(--muted); vertical-align: top; }}
    table.kv td {{ padding: 6px 8px; }}
    table.kv tr:nth-child(odd) td {{ background: rgba(255,255,255,0.02); }}

    pre.code {{ background: var(--code-bg); color: var(--code-text); padding: 10px 12px; border-radius: 8px; overflow: auto; white-space: pre-wrap; word-wrap: break-word; border: 1px solid #0f172a; }}

    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

    .footer {{ margin-top: 24px; font-size: 12px; color: var(--muted); text-align: right; }}

    /* Chat UI */
    .chat {{ display: flex; flex-direction: column; gap: 10px; }}
    .msg {{ max-width: 92%; display: flex; flex-direction: column; gap: 6px; }}
    .msg.user {{ align-self: flex-start; }}
    .msg.assistant {{ align-self: flex-end; }}
    .msg.system {{ align-self: center; max-width: 80%; }}
    .msg.toolcall {{ align-self: flex-start; }}
    .msg.toolresp {{ align-self: flex-start; }}
    .msg .header {{ font-size: 12px; color: var(--muted); }}
    .msg .header .idx {{ margin-left: 6px; font-weight: 600; color: #9fb2c8; }}
    .bubble {{ padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border); }}
    .msg.user .bubble {{ background: var(--bubble-user); }}
    .msg.assistant .bubble {{ background: var(--bubble-assistant); }}
    .msg.system .bubble {{ background: var(--bubble-system); }}
    .msg.toolcall .bubble {{ background: var(--bubble-toolcall); border-color: rgba(245,158,11,0.45); }}
    .msg.toolresp .bubble {{ background: var(--bubble-toolresp); border-color: rgba(58,160,255,0.45); }}
    .msg-text {{ white-space: pre-wrap; word-break: break-word; }}
    .thoughts {{ background: #10151f; border-left: 3px solid #a3a3a3; padding: 8px 10px; border-radius: 6px; margin-bottom: 8px; }}
    .thoughts-title {{ font-size: 12px; color: #9fb2c8; margin-bottom: 4px; font-weight: 600; }}

    /* Collapsible */
    details.collapsible {{ border: 1px dashed var(--border); border-radius: 8px; padding: 6px 8px; background: #0c1320; }}
    details.collapsible summary {{ cursor: pointer; color: #cde3ff; font-size: 12px; margin-bottom: 6px; }}
    .collapsible-body {{ margin-top: 6px; }}

    /* Badges */
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid var(--border); }}
    .badge-success {{ background: #14321d; color: #b7f7ce; border-color: rgba(34,197,94,0.4); }}
    .badge-failure {{ background: #3a1214; color: #fecaca; border-color: rgba(239,68,68,0.4); }}
    .badge-partial {{ background: #3a2a06; color: #fde68a; border-color: rgba(245,158,11,0.4); }}

    /* Print styles */
    @media print {{
      body {{ padding: 0; }}
      .no-print {{ display: none !important; }}
      .page-break {{ page-break-before: always; }}
      pre.code {{ white-space: pre-wrap; }}
      .msg, .card {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class=\"header\">
    <h1>{_escape_html(title)}</h1>
    <div class=\"ts\">Generated: {_escape_html(datetime.now().isoformat())}</div>
  </div>

  {toc_html}

  <div class=\"grid\" id=\"summary\">
    {_block("Evaluation Summary", _kv_table(eval_rows))}
    {_block("Meta", _kv_table(meta_rows), anchor="meta")}
  </div>

  {_block("Result Overview", overview_content_html)}

  {_block("Final Output (Raw)", _collapse_if_long(_code_block(final_output), "Final Output", str(final_output)))}

  <div class=\"final-step\">
    {final_step_html}
  </div>

  {timeline_section_html}

  <div class=\"page-break\"></div>
  {_block("Full Code", _collapse_if_long(_code_block(full_code), "Full Code", str(full_code)), anchor="full-code")}

  <div class=\"footer\">Report generated by visualization.visualizerun</div>
</body>
</html>
    """
    return html


def _write_text(path: str, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _try_install_playwright() -> None:
    """Best-effort installation of Playwright and Chromium browser.
    This attempts to:
      1) pip install playwright
      2) playwright install chromium
    All errors are swallowed; the caller should handle import errors.
    """
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], check=False)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    except Exception:
        pass


def _try_html_to_pdf_with_pdfkit(html_content: str, out_pdf: str) -> Tuple[bool, Optional[str]]:
    try:
        import pdfkit  # type: ignore
        try:
            pdfkit.from_string(html_content, out_pdf, options={"quiet": ""})
            return True, None
        except Exception as e:
            return False, f"pdfkit/wkhtmltopdf failed: {e}"
    except Exception as e:
        return False, f"pdfkit not available: {e}"


def _try_html_to_pdf_with_weasyprint(html_content: str, out_pdf: str) -> Tuple[bool, Optional[str]]:
    try:
        from weasyprint import HTML  # type: ignore
        try:
            HTML(string=html_content).write_pdf(out_pdf)
            return True, None
        except Exception as e:
            return False, f"WeasyPrint failed: {e}"
    except Exception as e:
        return False, f"WeasyPrint not available: {e}"


def _html_to_pdf(html_content: str, out_pdf: str) -> Tuple[bool, Optional[str]]:
    """Render HTML -> PDF using Playwright. Falls back to pdfkit/WeasyPrint if available.
    Returns (ok, error_msg)."""
    # First try Playwright
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as e:
        _try_install_playwright()
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e2:
            sync_playwright = None  # type: ignore
    else:
        # successfully imported
        pass

    if 'sync_playwright' in locals() and locals()['sync_playwright'] is not None:
        try:
            with locals()['sync_playwright']() as p:  # type: ignore
                browser = p.chromium.launch()
                page = browser.new_page()
                page.set_content(html_content, wait_until="load")
                page.pdf(
                    path=out_pdf,
                    format="A4",
                    print_background=True,
                    margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
                )
                browser.close()
            return True, None
        except Exception as e:
            # fallthrough to other engines
            last_err = f"Playwright rendering failed: {e}"
        else:
            last_err = None
    else:
        last_err = "Playwright not available"

    # Fallback 1: pdfkit/wkhtmltopdf
    ok, err = _try_html_to_pdf_with_pdfkit(html_content, out_pdf)
    if ok:
        return True, None
    if err:
        last_err = (last_err + "; " if last_err else "") + err

    # Fallback 2: WeasyPrint
    ok, err = _try_html_to_pdf_with_weasyprint(html_content, out_pdf)
    if ok:
        return True, None
    if err:
        last_err = (last_err + "; " if last_err else "") + err

    return False, last_err or "Unknown PDF rendering error"


def render_smolagent_run_to_pdf(json_path: str, out_basename: Optional[str] = None, include_timeline: bool = False) -> Dict[str, str]:
    """
    Render a smolagent run JSON to HTML, then export to PDF.

    Args:
      json_path: Absolute or relative path to smolagent_run.json
      out_basename: Optional basename for outputs (without extension). If None, use 'smolagent_run_report'.

    Returns:
      dict with keys: {'html': html_path, 'pdf': pdf_path (may be absent if failed)}
    """
    json_path = os.path.abspath(json_path)
    data = _read_json(json_path)

    # Determine output directory and names
    out_dir = os.path.dirname(json_path)
    base = out_basename or "smolagent_run_report"
    html_path = os.path.join(out_dir, f"{base}.html")
    pdf_path = os.path.join(out_dir, f"{base}.pdf")

    html = _build_html(data, json_path, include_timeline=include_timeline)
    _write_text(html_path, html)

    ok, err = _html_to_pdf(html, pdf_path)
    result = {"html": html_path}
    if ok:
        result["pdf"] = pdf_path
    else:
        result["pdf_error"] = err or "Unknown error"
    return result


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render smolagent run JSON to HTML + PDF")
    p.add_argument("--json", required=True, help="Path to smolagent_run.json")
    p.add_argument("--out", default=None, help="Output basename (no extension). Default: smolagent_run_report")
    p.add_argument("--include-timeline", action="store_true", help="Include the full steps timeline section")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    if not os.path.exists(args.json):
        print(f"[Error] JSON not found: {args.json}", file=sys.stderr)
        return 2
    try:
        res = render_smolagent_run_to_pdf(args.json, args.out, include_timeline=args.include_timeline)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if "pdf" in res:
            print(f"[OK] HTML: {res['html']}\n[OK] PDF: {res['pdf']}")
        else:
            print(f"[OK] HTML: {res['html']}\n[WARN] PDF not generated: {res.get('pdf_error')}")
        return 0
    except Exception as e:
        print(f"[Error] Failed to render: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
