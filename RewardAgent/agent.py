"""
RewardAgent: A GUI reward/assessment agent built on top of smolagents.CodeAgent.

This agent wraps a CodeAgent and injects a custom system prompt (instructions) so that
the LLM generates Python code actions and returns a final answer via the `final_answer` tool.
The `evaluate` method provides a simple interface to judge whether a GUI task is completed,
returning a JSON-like result with keys: reward (float), verdict (str), reasoning (str).
"""

from __future__ import annotations

import json
import re
import os
import datetime
from typing import Optional, List, Dict, Any

from smolagents import CodeAgent, Tool
import smolagents
print(f"smolagents file location: {smolagents.__file__}")
from visualization.visualizerun import render_smolagent_run_to_pdf
from RewardAgent.prompts.system_prompt import system_prompt as DEFAULT_SYSTEM_PROMPT
from RewardAgent.prompts.prompt_builder import build_evaluation_prompt
from RewardAgent.prompts.evaluation_templates import get_evaluation_prompt_templates
from RewardAgent.tools.CaptionImage import CaptionImageTool
from RewardAgent.tools.final_answer import FinalAnswerTool
from RewardAgent.tools.computer_use import ComputerUseTool
from RewardAgent.tools.ObserveCurrentState import ObserveCurrentStateTool
# Lazy import of environment tools to avoid dependency issues
# from RewardAgent.tools.environment_tools import (...)

class RewardAgent:
    """
    RewardAgent:
    - A wrapper that uses a single persistent CodeAgent instance (created in __init__)
    - evaluate() updates the agent's tools and prompt templates dynamically
    - No repeated instantiation of CodeAgent during evaluation
    """

    def __init__(
        self,
        llm,
        env: Any,
        system_prompt: Optional[str] = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = 20,
        tools: Optional[List[Tool]] = None,
        add_base_tools: bool = False,
        trajectory_dir: Optional[str] = None,
        app: str = "all",
        **kwargs,
    ):
        """
        Initialize the RewardAgent.

        Args:
            llm: The language model (LLM) implementing smolagents Model interface
            env: The desktop environment object (required for most tools)
            system_prompt: Base system prompt for evaluation instructions
            max_iterations: Maximum reasoning/tool-calling steps (default: 6)
            tools: Custom set of smolagents Tools (default: auto-built from env)
            add_base_tools: Whether to include smolagents' built-in tools (default: False)
            trajectory_dir: Optional path to trajectory images directory
            app: Which app toolset to load. 'all' for everything; otherwise only that app's tools
                 plus always-on tools [final_answer, execute_vm_command, get_vm_command_error,
                 get_vm_file].
            **kwargs: Additional parameters forwarded to CodeAgent

        The base CodeAgent is created only once and reused by evaluate().
        """
        if env is None:
            raise ValueError("env parameter is required for RewardAgent initialization.")
            
        self.llm = llm
        self.env = env
        self.trajectory_dir = trajectory_dir
        self.base_system_prompt = system_prompt
        self.base_max_iterations = max_iterations
        self.base_kwargs = kwargs
        self.app = (app or "all").lower()

        # Build tools with env
        if tools is None:
            tools = self._build_tools(trajectory_dir, env, self.app)
        else:
            # Respect custom tools, but ensure always-on tools exist
            ensured = {getattr(t, "name", "") for t in tools}
            # Always-on tools
            from RewardAgent.tools.environment_tools import (
                VMCommandLineTool,
                VMCommandErrorTool,
                VMFileTool,
                VMTerminalOutputTool,
            )
            from RewardAgent.tools.file_getters import GetHostFileContentTool
            from RewardAgent.tools.app_getters import GetAccessibilityTreeTool

            if "final_answer" not in ensured:
                tools.append(FinalAnswerTool())
            if "execute_vm_command" not in ensured:
                tools.append(VMCommandLineTool(env))
            if "get_vm_command_error" not in ensured:
                tools.append(VMCommandErrorTool(env))
            if "get_vm_file" not in ensured:
                tools.append(VMFileTool(env))
            # if "get_terminal_output" not in ensured:
            #     tools.append(VMTerminalOutputTool(env))
            if "get_host_file_content" not in ensured:
                tools.append(GetHostFileContentTool())
            if "get_accessibility_tree" not in ensured:
                tools.append(GetAccessibilityTreeTool(env))
            # Observation tool: default read-only screenshot+caption
            if "observe_current_state" not in ensured:
                tools.append(ObserveCurrentStateTool(env))
            if "computer_use" not in ensured:
                tools.append(ComputerUseTool(env))
            # trajectory tool is optional: only when provided
            if trajectory_dir is not None and not any(isinstance(t, CaptionImageTool) for t in tools):
                tools.append(CaptionImageTool())

        # Keep a reference to tool instances for later updates (e.g., setting output_dir)
        self.tools = tools
        
        # Generate enhanced system prompt with tool documentation
        enhanced_prompt = self._generate_enhanced_prompt(system_prompt, tools, trajectory_dir, env)
        prompt_templates = get_evaluation_prompt_templates(enhanced_prompt)
        # print(f"prompt_templates:{prompt_templates}")
        # Create persistent CodeAgent ONCE
        self.agent = CodeAgent(
            tools=tools,
            model=llm,
            max_steps=max_iterations,
            prompt_templates=prompt_templates,
            add_base_tools=add_base_tools,
            **kwargs,
        )


    def _build_tools(self, trajectory_dir, env, app: str) -> List[Tool]:
        """
        Build available tools based on the selected app and always-on set.
        smolagents internally converts [tools] into a dict {tool.name: tool}.
        """
        tools: List[Tool] = []
        
        # Always-on terminal tool to finish evaluation
        tools.append(FinalAnswerTool())

        # Trajectory tool (image analysis) if available
        if trajectory_dir is not None:
            tools.append(CaptionImageTool())

        if env is None:
            return tools

        app = (app or "all").lower()

        # Always-on environment/file tools
        from RewardAgent.tools.environment_tools import (
            VMCommandLineTool,
            VMCommandErrorTool,
            VMFileTool,
            VMTerminalOutputTool,
        )
        from RewardAgent.tools.file_getters import GetHostFileContentTool
        from RewardAgent.tools.app_getters import GetAccessibilityTreeTool
        tools.extend([
            VMCommandLineTool(env),
            VMCommandErrorTool(env),
            VMFileTool(env),
            VMTerminalOutputTool(env),
            GetHostFileContentTool(),
            GetAccessibilityTreeTool(env),
        ])
        # Read-only observation tool (preferred for initial context gathering)
        tools.append(ObserveCurrentStateTool(env))
        # Computer use tool (GUI interaction)
        tools.append(ComputerUseTool(env))

        def add_system_tools():
            print("no os tools ")

        def add_chrome_tools():
            from RewardAgent.tools.chrome_getters import (
                GetActiveTabInfoTool,
                GetDefaultSearchEngineTool,
                GetCookieDataTool,
                GetBookmarksTool,
                GetOpenTabsInfoTool,
                GetBrowserHistoryTool,
                GetPageInfoTool,
                GetChromeLanguageTool,
                GetChromeFontSizeTool,
            )
            from RewardAgent.tools.environment_tools import GetActiveURLTool
            tools.extend([
                GetActiveTabInfoTool(env),
                GetDefaultSearchEngineTool(env),
                GetCookieDataTool(env),
                GetBookmarksTool(env),
                GetOpenTabsInfoTool(env),
                GetBrowserHistoryTool(env),
                GetPageInfoTool(env),
                GetChromeLanguageTool(env),
                GetChromeFontSizeTool(env),
                GetActiveURLTool(env),
            ])

        def add_vscode_tools():
            from RewardAgent.tools.vscode_getters import (
                GetVSCodeUserSettingsFileTool,
                GetVSCodeKeybindingsFileTool,
            )
            tools.extend([
                GetVSCodeUserSettingsFileTool(env),
                GetVSCodeKeybindingsFileTool(env),
            ])

        def add_thunderbird_tools():
            from RewardAgent.tools.thunderbird import (
                GetThunderbirdPrefsFileTool,
                GetThunderbirdActiveThemeTool,
                GetThunderbirdRegionTool,
                GetThunderbirdTimezoneTool,
                GetThunderbirdUseSystemTimezoneTool,
                GetThunderbirdAccountsTool,
            )
            tools.extend([
                GetThunderbirdPrefsFileTool(env),
                GetThunderbirdActiveThemeTool(),
                GetThunderbirdRegionTool(),
                GetThunderbirdTimezoneTool(),
                GetThunderbirdUseSystemTimezoneTool(),
                GetThunderbirdAccountsTool(),
            ])

        def add_ppt_tools():
            from RewardAgent.tools.impress_getters import (
                GetPptConfigFileTool,
                # FindDefaultFontTool,
                # CheckAutoSavingTimeTool,
                # CheckPresenterConsoleDisabledTool,
                # CheckPageNumberColorsTool,
                # CheckTransitionTool,
                # CheckSlideOrientationPortraitTool,
                # CheckLeftPanelTool,
            )

            # Minimized PPT toolset per design: keep only generic getters
            tools.extend([
                GetPptConfigFileTool(env)
            ])
            # Doc-check for PPT
            from RewardAgent.tools.CheckPptFile import CheckPptFileTool
            tools.append(CheckPptFileTool())
            # PPT XML getter (OOXML slide reader)
            from RewardAgent.tools.GetPptXml import GetPptXmlTool
            tools.append(GetPptXmlTool())

        def add_word_tools():
            from RewardAgent.tools.doc_getters import (
                ContainsPageBreakTool,
                HasPageNumbersInFootersTool,
                FirstLineCenteredTool,
                DocxSpacingPatternTool,
                DocxConvertedLowercaseTool,
                DocxAlignmentPatternTool,
                DocxStrikeThroughLastParagraphTool,
                DocxItalicFontSize14Tool,
            )
            tools.extend([
                ContainsPageBreakTool(),
                HasPageNumbersInFootersTool(),
                FirstLineCenteredTool(),
                DocxSpacingPatternTool(),
                DocxConvertedLowercaseTool(),
                DocxAlignmentPatternTool(),
                DocxStrikeThroughLastParagraphTool(),
                DocxItalicFontSize14Tool(),
            ])
            # Doc-check for Word
            from RewardAgent.tools.CheckWordFile import CheckWordFileTool
            tools.append(CheckWordFileTool())

        def add_excel_tools():
            from RewardAgent.tools.file_getters import GetXlsxContentTool
            tools.append(GetXlsxContentTool(env))
            # Doc-check for Excel
            from RewardAgent.tools.CheckExcelFile import CheckExcelFileTool
            tools.append(CheckExcelFileTool())

        def add_vlc_tools():
            from RewardAgent.tools.app_getters import (
                GetVLCPlayingInfoTool,
                GetVLCConfigTool,
                GetDefaultVideoPlayerTool,
            )
            tools.extend([
                GetVLCPlayingInfoTool(env),
                GetVLCConfigTool(env),
                GetDefaultVideoPlayerTool(env),
            ])

        def add_gimp_tools():
            from RewardAgent.tools.app_getters import GetGimpConfigFileTool
            tools.append(GetGimpConfigFileTool(env))

        def add_file_ops_tools():
            # Additional file ops that are NOT always-on
            from RewardAgent.tools.file_getters import (
                GetCloudFileTool,
                GetCacheFileTool,
            )
            tools.extend([
                GetCloudFileTool(env), 
                GetCacheFileTool(env),
            ])

        if app in {"all","multi_apps"}:
            add_system_tools()
            add_chrome_tools()
            add_vscode_tools()
            add_thunderbird_tools()
            add_ppt_tools()
            add_word_tools()
            add_excel_tools()
            add_vlc_tools()
            add_gimp_tools()
            add_file_ops_tools()
        else:
            if app in {"system", "os"}:
                add_system_tools()
            elif app == "chrome":
                add_chrome_tools()
            elif app == "vs_code":
                add_vscode_tools()
            elif app == "thunderbird":
                add_thunderbird_tools()
            elif app in {"ppt", "impress",'libreoffice_impress'}:
                add_ppt_tools()
            elif app in {"word", "writer",'libreoffice_writer'}: 
                add_word_tools()
            elif app in {"excel", "calc",'libreoffice_calc'}:
                add_excel_tools()
            elif app == "vlc":
                add_vlc_tools()
            elif app == "gimp":
                add_gimp_tools()
            else:
                # Unknown app: only keep always-on + optional caption tool
                pass

        return tools

    def _generate_enhanced_prompt(
        self, 
        base_prompt: str, 
        tools: List[Tool], 
        trajectory_dir: Optional[str], 
        env: Any
    ) -> str:
        """
        Generate enhanced system prompt with automatic tool documentation.
        
        Args:
            base_prompt: Base system prompt text
            tools: List of available tools
            trajectory_dir: Optional trajectory directory
            env: Environment object
            
        Returns:
            Enhanced prompt with tool documentation
        """
        # Build mode-specific guidance using prompt_builder
        mode_prompt = build_evaluation_prompt(
            base_prompt=base_prompt,
            has_trajectory=bool(trajectory_dir),
            has_env=env is not None
        )
        enhanced_parts = [mode_prompt]
        
        # Add tool documentation section to the end
        enhanced_parts.append("\n\n---\n\n### 🛠️ Available Tools")
        enhanced_parts.append("\nYou have access to the following tools for evaluation:\n")
        
        # Categorize tools for better organization
        tool_categories = {
            "Image Analysis": [],
            "System Information": [],
            "Chrome Browser": [],
            "Application Specific": [],
            "File Operations": [],
            "Environment Control": [],
            "Other": []
        }
        
        # Categorize tools based on their names and descriptions
        for tool in tools:
            tool_name = tool.name.lower()
            if "caption" in tool_name or "image" in tool_name:
                tool_categories["Image Analysis"].append(tool)
            elif any(x in tool_name for x in ["screen", "window", "wallpaper", "directory", "vm_"]):
                tool_categories["System Information"].append(tool)
            elif any(x in tool_name for x in ["chrome", "tab", "browser", "bookmark", "cookie", "search"]):
                tool_categories["Chrome Browser"].append(tool)
            elif any(x in tool_name for x in ["vscode", "vlc", "gimp", "conference", "slide", "video", "thunderbird"]):
                tool_categories["Application Specific"].append(tool)
            elif any(x in tool_name for x in ["file", "cloud", "cache"]):
                tool_categories["File Operations"].append(tool)
            elif any(x in tool_name for x in ["command", "terminal", "execute"]):
                tool_categories["Environment Control"].append(tool)
            else:
                tool_categories["Other"].append(tool)
        
        # Generate documentation for each category
        for category, category_tools in tool_categories.items():
            if not category_tools:
                continue
                
            enhanced_parts.append(f"\n#### {category}:\n")
            
            for tool in category_tools:
                # Get tool signature from to_code_prompt method
                try:
                    code_signature = tool.to_code_prompt()
                    enhanced_parts.append(f"```python\n{code_signature}\n```")
                    
                    # Add tool description if available
                    if hasattr(tool, 'description') and tool.description:
                        enhanced_parts.append(f"*{tool.description}*\n")
                    
                except (AttributeError, Exception) as e:
                    # Fallback if to_code_prompt is not available
                    enhanced_parts.append(f"- `{tool.name}`: {getattr(tool, 'description', 'No description available')}\n")
        
        # Add usage guidelines
        # enhanced_parts.append("\n#### 📋 Tool Usage Guidelines:\n")
        # enhanced_parts.append("1. **Image Analysis**: Use `caption_image` to analyze GUI screenshots and understand visual changes\n")
        # enhanced_parts.append("2. **System Information**: Check screen resolution, window states, and system configuration\n") 
        # enhanced_parts.append("3. **Chrome Browser**: Verify web page states, URLs, bookmarks, and browser settings\n")
        # enhanced_parts.append("4. **Application Specific**: Check application configurations and states (VSCode, VLC, GIMP, LibreOffice)\n")
        # enhanced_parts.append("5. **File Operations**: Access and verify file contents, cloud files, and cached data\n")
        # enhanced_parts.append("6. **Environment Control**: Execute system commands and check terminal output\n")
        # enhanced_parts.append("\n**Strategy**: Combine multiple tools to build comprehensive understanding of task completion.\n")
        
        # Add context-specific guidance
        if trajectory_dir:
            enhanced_parts.append("\n#### 🎯 Trajectory Evaluation Context:\n")
            enhanced_parts.append("- Screenshot analysis is available via `caption_image`\n")
            enhanced_parts.append("- Compare initial vs final states to assess progress\n")
            enhanced_parts.append("- Look for visual evidence of task completion\n")
        
        if env:
            enhanced_parts.append("\n#### 🔧 Environment Access Available:\n") 
            enhanced_parts.append("- Live system state inspection capabilities\n")
            enhanced_parts.append("- Real-time application and browser state verification\n")
            enhanced_parts.append("- File system and configuration access\n")
        
        return "".join(enhanced_parts)

    def evaluate(
        self,
        task_instruction: str,
        apps: List[str],
        trajectory_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate whether a GUI task was completed successfully.

        Args:
            task_instruction: Natural language description of the task to evaluate
            trajectory_dir: Path to directory containing GUI screenshots

        Returns:
            Dict with keys:
                - reward: float (0.0-1.0) indicating task completion level
                - verdict: str ("Success", "Partial Success", or "Failure")  
                - reasoning: str explaining the evaluation decision

        Raises:
            RuntimeError: If evaluation fails or output cannot be parsed
        """

        trajectory_images = []
        if trajectory_dir is not None:
            trajectory_images = self._load_trajectory_images(trajectory_dir)
        
        # Create evaluation task prompt
        eval_task = self._build_evaluation_task(task_instruction, apps, trajectory_dir, trajectory_images)

        try:
            # Propagate output_dir to doc-check tools
            if output_dir:
                try:
                    for t in getattr(self, "tools", []) or []:
                        if getattr(t, "name", "") in ("checkexcelfile", "checkpptfile", "checkwordfile") and hasattr(t, "set_output_dir"):
                            t.set_output_dir(output_dir)
                        # Propagate to computer_use tool
                        if getattr(t, "name", "") == "computer_use" and hasattr(t, "set_output_dir"):
                            t.set_output_dir(output_dir)
                        # Propagate to observe_current_state tool
                        if getattr(t, "name", "") == "observe_current_state" and hasattr(t, "set_output_dir"):
                            t.set_output_dir(output_dir)
                except Exception as e:
                    print(f"[RewardAgent] Failed to propagate output_dir to doc tools: {e}")
            result = self.agent.run(eval_task)
            
            # Parse and validate output
            evaluation = self._parse_evaluation_result(result)
            
            # Save smolagents run log if requested
            if output_dir:
                try:
                    self._save_agent_run_log(
                        output_dir=output_dir,
                        task_instruction=task_instruction,
                        trajectory_dir=trajectory_dir,
                        evaluation=evaluation,
                        final_output=result,
                    )
                    # Auto-generate HTML report from the saved JSON (no auto-open, no timeline)
                    try:
                        json_path = os.path.join(output_dir, "reward_log", "smolagent_run.json")
                        res = render_smolagent_run_to_pdf(json_path, out_basename=None, include_timeline=False)
                        print(f"[RewardAgent] HTML report generated: {res.get('html')}")
                        if 'pdf' in res:
                            print(f"[RewardAgent] PDF generated: {res.get('pdf')}")
                        else:
                            err = res.get('pdf_error')
                            if err:
                                print(f"[RewardAgent] PDF not generated: {err}")
                    except Exception as viz_e:
                        print(f"[RewardAgent] Failed to render HTML report: {viz_e}")
                except Exception as log_e:
                    print(f"[RewardAgent] Failed to save smolagent run log: {log_e}")
            
            return evaluation
            
        except Exception as e:
            raise RuntimeError(f"Evaluation failed: {str(e)}") from e

    def _build_evaluation_task(
        self,
        task_instruction: str,
        apps: List[str],
        trajectory_dir: Optional[str],
        trajectory_images: Optional[List[str]] = None
    ) -> str:
        """
        Construct the evaluation task prompt sent to CodeAgent.

        Args:
            task_instruction: Human-readable task to evaluate
            trajectory_dir: Directory containing screenshot images  
            trajectory_images: Pre-loaded list of image paths

        Returns:
            Formatted prompt string describing evaluation task and context
        """
        task_parts = [
            "# Task Evaluation Request\n",
            f"\n**Task Instruction**: {task_instruction}\n",
            f"\n**Related apps**: {apps}\n"
        ]

        if trajectory_dir and trajectory_images:
            task_parts.append(f"\n**Trajectory Directory**: {trajectory_dir}\n")
            task_parts.append(f"\n**Total Steps**: {len(trajectory_images)}\n")
            task_parts.append("\n**Available Trajectory Images**:\n")
            for img_path in trajectory_images:
                task_parts.append(f"  - {img_path}\n")
            task_parts.append(
                "\nUse the caption_image tool to analyze these images.\n"
            )

        task_parts.append(
            "\n## Your Mission\n"
            "Evaluate whether the task described above has been successfully completed.\n"
        )

        return "".join(task_parts)

    def _load_trajectory_images(self, trajectory_dir: str) -> List[str]:
        """
        Load and numerically sort screenshot images from trajectory directory.

        Args:
            trajectory_dir: Path to directory containing GUI screenshots

        Returns:
            Sorted list of absolute file paths to images
        """
        import os

        if not os.path.exists(trajectory_dir):
            return []

        image_files = [
            os.path.join(trajectory_dir, f)
            for f in os.listdir(trajectory_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        def numerical_sort(filename: str) -> int:
            import re
            numbers = re.findall(r"\d+", os.path.basename(filename))
            return int(numbers[-1]) if numbers else 0

        return sorted(image_files, key=numerical_sort)

    def _parse_evaluation_result(self, result: str) -> Dict[str, Any]:
        """
        Extract and validate JSON evaluation output from LLM result.

        Args:
            result: Raw text output from CodeAgent.run()

        Returns:
            Parsed evaluation dict with reward, verdict, and reasoning

        Raises:
            RuntimeError: If JSON cannot be parsed or required fields are invalid
        """
        import json
        import re

        # Case 1: handle final_answer(...) format
        final_answer_match = re.search(r'final_answer\(\s*"reward"\s*:\s*([^,]+)\s*,\s*"verdict"\s*:\s*([^,]+)\s*,\s*"reasoning"\s*:\s*([^)]+)\s*\)', result)
        if final_answer_match:
            try:
                reward_f = float(final_answer_match.group(1).strip())
                # Strip surrounding quotes from the extracted verdict
                verdict = final_answer_match.group(2).strip().strip('\"\'')
                # Strip surrounding quotes from the extracted reasoning
                reasoning_s = final_answer_match.group(3).strip().strip('\"\'')
                
                evaluation = {
                    "reward": reward_f,
                    "verdict": verdict,
                    "reasoning": reasoning_s
                }
                
                # Validate the extracted fields
                if not (0 <= reward_f <= 1):
                    raise RuntimeError(f"Reward must be in [0, 1], got: {reward_f}")
                
                valid_verdicts = ["Success", "Partial Success", "Failure"]
                if verdict not in valid_verdicts:
                    raise RuntimeError(f"Verdict must be one of {valid_verdicts}, got: {verdict}")
                
                return evaluation
            except (ValueError, Exception) as e:
                # Parsing failed; fall through and try other formats
                pass

        # Case 2: handle plain JSON format
        try:
            # First try to extract JSON from a fenced code block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Otherwise try to extract a JSON object containing a "reward" field
                json_match = re.search(r'\{[^{}]*"reward"[^{}]*\}', result, re.DOTALL)
                if not json_match:
                    # Case 3: neither final_answer nor JSON format; evaluation failed
                    raise RuntimeError(
                        f"Evaluation failed: Could not find valid evaluation format. "
                        f"Output was: {result[:500]}..."
                    )
                json_str = json_match.group(0)

            # Parse the JSON
            evaluation = json.loads(json_str)

            # Validate required fields
            required = ["reward", "verdict", "reasoning"]
            missing = [f for f in required if f not in evaluation]
            if missing:
                raise RuntimeError(f"Missing fields in evaluation result: {missing}")

            # Validate reward
            reward = evaluation["reward"]
            if not isinstance(reward, (int, float)) or not (0 <= reward <= 1):
                raise RuntimeError(f"Reward must be in [0, 1], got: {reward}")

            # Validate verdict
            valid_verdicts = ["Success", "Partial Success", "Failure"]
            if evaluation["verdict"] not in valid_verdicts:
                raise RuntimeError(
                    f"Verdict must be one of {valid_verdicts}, got: {evaluation['verdict']}"
                )

            return evaluation
        except (json.JSONDecodeError, RuntimeError) as e:
            # Case 3: parsing failed; evaluation failed
            raise RuntimeError(f"Evaluation failed: {str(e)}") from e
        
    def _save_agent_run_log(
        self,
        output_dir: str,
        task_instruction: str,
        trajectory_dir: Optional[str],
        evaluation: Dict[str, Any],
        final_output: str,
    ) -> None:
        """
        Save smolagents CodeAgent run details (full steps and code) into output_dir/reward_log.
        - smolagent_run.json: meta, evaluation, final_output, full_code, steps (images stripped)
        - smolagent_full_code.py: concatenated Python code produced during the run
        """
        try:
            reward_log_dir = os.path.join(output_dir, "reward_log")
            os.makedirs(reward_log_dir, exist_ok=True)

            steps = []
            full_code = ""
            if hasattr(self.agent, "memory") and getattr(self.agent, "memory") is not None:
                try:
                    steps = self.agent.memory.get_full_steps() or []
                except Exception:
                    steps = []
                try:
                    full_code = self.agent.memory.return_full_code() or ""
                except Exception:
                    full_code = ""

            def _strip_large_fields(obj):
                if isinstance(obj, dict):
                    new_d = {}
                    for k, v in obj.items():
                        lk = k.lower()
                        # Drop large/binary image-like fields
                        if lk in (
                            "observations_images",
                            "observation_images",
                            "images",
                            "image",
                            "screenshot",
                            "screenshot_b64",
                            "image_bytes",
                        ):
                            continue
                        new_d[k] = _strip_large_fields(v)
                    return new_d
                elif isinstance(obj, list):
                    return [_strip_large_fields(x) for x in obj]
                else:
                    return obj

            safe_steps = _strip_large_fields(steps)

            payload = {
                "meta": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "task_instruction": task_instruction,
                    "trajectory_dir": trajectory_dir,
                    "max_steps": getattr(self, "base_max_iterations", None),
                    "model_id": getattr(self.llm, "model_id", None),
                    "agent_class": type(self.agent).__name__,
                },
                "evaluation": evaluation,
                "final_output": final_output,
                "full_code": full_code,
                "steps": safe_steps,
            }

            json_path = os.path.join(reward_log_dir, "smolagent_run.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

            if full_code:
                code_path = os.path.join(reward_log_dir, "smolagent_full_code.py")
                with open(code_path, "w", encoding="utf-8") as f:
                    f.write(full_code)
        except Exception as e:
            # Don't let logging failures break the main evaluation flow
            print(f"[RewardAgent] _save_agent_run_log error: {e}")
