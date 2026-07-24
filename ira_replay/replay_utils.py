from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _normalise_action_entry(entry: Any, index: int) -> dict[str, Any]:
    if isinstance(entry, str):
        return {"step_num": index + 1, "action": entry}
    if not isinstance(entry, dict):
        raise TypeError(f"Trajectory entry {index + 1} must be a dict or action string.")
    if "action" not in entry:
        raise KeyError(f"Trajectory entry {index + 1} is missing the 'action' field.")
    return {
        "step_num": entry.get("step_num", index + 1),
        "action": entry["action"],
    }


def _write_screenshot(obs: dict[str, Any], path: Path) -> bool:
    screenshot = obs.get("screenshot") if isinstance(obs, dict) else None
    if screenshot is None:
        return False
    if isinstance(screenshot, bytes):
        path.write_bytes(screenshot)
        return True
    if isinstance(screenshot, str) and os.path.exists(screenshot):
        shutil.copyfile(screenshot, path)
        return True
    return False


def replay_trajectory_only(
    env: Any,
    *,
    source_trajectory_dir: Optional[str | Path] = None,
    output_trajectory_dir: str | Path,
    sleep_after_execution: float = 0.5,
    reset_wait_seconds: float = 60.0,
    inter_step_wait_seconds: float = 2.0,
    traj_data: Optional[Iterable[Any]] = None,
    task_config: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Replay a recorded GUI trajectory without calling ``env.evaluate()``.

    The original research runner used this ordering to keep the final desktop
    state clean for a reward evaluator: reset task, replay actions, let IRA
    inspect the final state, then call the environment's ground-truth evaluator.
    """
    output_dir = Path(output_trajectory_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_dir = Path(source_trajectory_dir) if source_trajectory_dir else None
    if task_config is None:
        if source_dir is None:
            raise ValueError("task_config is required when source_trajectory_dir is not set.")
        task_config = json.loads((source_dir / "task_config.json").read_text(encoding="utf-8"))

    (output_dir / "task_config.json").write_text(
        json.dumps(task_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if traj_data is None:
        if source_dir is None:
            raise ValueError("traj_data is required when source_trajectory_dir is not set.")
        raw_actions = _load_jsonl(source_dir / "traj.jsonl")
    else:
        raw_actions = list(traj_data)

    actions = [_normalise_action_entry(entry, idx) for idx, entry in enumerate(raw_actions)]
    logger.info("Replaying %d trajectory steps without env.evaluate().", len(actions))

    env.reset(task_config=task_config)
    if reset_wait_seconds > 0:
        time.sleep(reset_wait_seconds)

    initial_state_path: Optional[Path] = None
    try:
        obs = env._get_obs()
        candidate = output_dir / "initial_state_after_reset.png"
        if _write_screenshot(obs, candidate):
            initial_state_path = candidate
    except Exception as exc:  # pragma: no cover - depends on external desktop_env.
        logger.warning("Could not capture initial reset screenshot: %s", exc)

    traj_path = output_dir / "traj.jsonl"
    with traj_path.open("w", encoding="utf-8") as traj_file:
        for idx, entry in enumerate(actions):
            step_num = entry["step_num"]
            action = entry["action"]
            timestamp = _dt.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Replay step %s/%s: %s", step_num, len(actions), action)

            obs, reward, done, info = env.step(action, sleep_after_execution)
            screenshot_filename = f"step_{step_num}_{timestamp}.png"
            _write_screenshot(obs, output_dir / screenshot_filename)

            replay_entry = {
                "step_num": step_num,
                "action_timestamp": timestamp,
                "action": action,
                "reward": reward,
                "done": done,
                "info": info,
                "screenshot_file": screenshot_filename,
            }
            traj_file.write(json.dumps(replay_entry, ensure_ascii=False) + "\n")

            if done:
                logger.info("Environment reported done during replay.")
                break

            if idx < len(actions) - 1:
                wait_seconds = max(0.0, inter_step_wait_seconds - sleep_after_execution)
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

    return str(initial_state_path) if initial_state_path else None
