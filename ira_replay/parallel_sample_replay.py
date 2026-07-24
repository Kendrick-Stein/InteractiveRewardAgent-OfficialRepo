from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import json
import logging
import os
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Optional

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional for dry-run and installed via requirements.txt.
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

from .replay_utils import replay_trajectory_only

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "parallel_sample_replay.yaml"
TIMESTAMP_SUFFIX_RE = re.compile(r"-(\d{8}_\d{6})$")

CATEGORY_TO_TOOL_APP = {
    "chrome": "chrome",
    "vs_code": "vscode",
    "thunderbird": "thunderbird",
    "libreoffice_impress": "impress",
    "libreoffice_writer": "writer",
    "libreoffice_calc": "calc",
    "vlc": "vlc",
    "gimp": "gimp",
    "os": "os",
    "multi_apps": "all",
}


def _configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(asctime)s %(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_path(value: str | Path, *, base: Path = REPO_ROOT) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _load_config(path: str | Path) -> dict[str, Any]:
    config_path = _resolve_path(path)
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Run from a source checkout of the repository or pass --config <path>."
        )
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    config["_config_path"] = str(config_path)
    return config


def _safe_float(value: Any) -> Optional[float]:
    try:
        if isinstance(value, str):
            value = value.strip()
        return float(value)
    except Exception:
        return None


def _infer_tool_app(category: str, configured_tool_app: str) -> str:
    if configured_tool_app == "auto":
        return CATEGORY_TO_TOOL_APP.get(category, "all")
    return CATEGORY_TO_TOOL_APP.get(category, configured_tool_app) if configured_tool_app == "all" else configured_tool_app


def _task_id_from_path(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("id", path.stem)
    except Exception:
        return path.stem


def _extract_task_id_from_dirname(dirname: str) -> Optional[str]:
    if not dirname.startswith("replay-"):
        return None
    rest = dirname[len("replay-") :]
    match = TIMESTAMP_SUFFIX_RE.search(rest)
    if not match:
        return None
    task_id = rest[: match.start()]
    return task_id or None


def _has_complete_run(task_id: str, output_root: Path, cleanup_incomplete: bool = True, require_comparison: bool = False) -> bool:
    """Check for a finished replay of task_id.

    With require_comparison=True (reward agent enabled), a directory holding
    only ground_truth.json (from an earlier reward-agent-disabled run) does
    not count as complete, so the task is re-run to produce the comparison.
    """
    if not output_root.is_dir():
        return False
    found = False
    for child in output_root.iterdir():
        if not child.is_dir() or _extract_task_id_from_dirname(child.name) != task_id:
            continue
        comparison = child / "reward_log" / "comparison.json"
        ground_truth = child / "reward_log" / "ground_truth.json"
        if comparison.is_file() or (not require_comparison and ground_truth.is_file()):
            found = True
        elif cleanup_incomplete:
            logger.warning("Removing incomplete replay directory: %s", child)
            shutil.rmtree(child, ignore_errors=True)
    return found


def _load_existing_result(task_id: str, output_root: Path) -> Optional[dict[str, Any]]:
    if not output_root.is_dir():
        return None
    candidates: list[Path] = []
    for child in output_root.iterdir():
        if child.is_dir() and _extract_task_id_from_dirname(child.name) == task_id:
            candidates.append(child)
    if not candidates:
        return None
    latest = sorted(candidates, key=lambda p: p.name, reverse=True)[0]
    reward_log = latest / "reward_log"
    comparison_path = reward_log / "comparison.json"
    ground_truth_path = reward_log / "ground_truth.json"

    record: dict[str, Any] = {
        "id": task_id,
        "status": "skip_existing",
        "output_dir": str(latest),
        "comparison_path": None,
        "evaluation_path": None,
        "reward_agent_reward": None,
        "ground_truth_score": None,
        "verdict": None,
        "match_binary": None,
        "match_strict_equal": None,
        "difference": None,
    }
    if comparison_path.is_file():
        data = json.loads(comparison_path.read_text(encoding="utf-8"))
        reward_agent = data.get("reward_agent", {}) or {}
        ground_truth = data.get("ground_truth", {}) or {}
        record.update(
            {
                "comparison_path": str(comparison_path),
                "reward_agent_reward": _safe_float(reward_agent.get("reward")),
                "ground_truth_score": _safe_float(ground_truth.get("score")),
                "verdict": reward_agent.get("verdict"),
                "match_binary": data.get("match_binary"),
                "match_strict_equal": data.get("match_strict_equal"),
                "difference": data.get("difference"),
            }
        )
    elif ground_truth_path.is_file():
        data = json.loads(ground_truth_path.read_text(encoding="utf-8"))
        record.update(
            {
                "comparison_path": str(ground_truth_path),
                "ground_truth_score": _safe_float(data.get("score")),
                "verdict": "NoRewardAgent",
            }
        )
    evaluation_path = reward_log / "evaluation.json"
    if evaluation_path.is_file():
        record["evaluation_path"] = str(evaluation_path)
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        record["eval_steps"] = evaluation.get("steps")
    task_config_path = latest / "task_config.json"
    if task_config_path.is_file():
        task_config = json.loads(task_config_path.read_text(encoding="utf-8"))
        traj = task_config.get("traj")
        record["traj_steps"] = len(traj) if isinstance(traj, list) else None
    return record


def _load_task_list_json(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Task list must be a category-to-id mapping: {path}")
    return {str(category): [str(item) for item in ids] for category, ids in data.items() if isinstance(ids, list)}


def collect_tasks(config: dict[str, Any]) -> list[dict[str, str]]:
    task_cfg = config.get("tasks", {}) or {}
    examples_dir = _resolve_path(task_cfg.get("examples_dir", "rewardbench_examples"))
    if not examples_dir.is_dir():
        raise FileNotFoundError(f"examples_dir does not exist: {examples_dir}")

    categories = task_cfg.get("categories") or []
    task_ids = set(str(item) for item in (task_cfg.get("task_ids") or []))
    task_list_json = task_cfg.get("task_list_json")
    max_per_category = task_cfg.get("max_tasks_per_category")
    max_total = task_cfg.get("max_tasks_total")

    selected_by_list: dict[str, set[str]] = {}
    if task_list_json:
        selected_by_list = {
            category: set(ids)
            for category, ids in _load_task_list_json(_resolve_path(task_list_json)).items()
        }
        if not categories:
            categories = list(selected_by_list.keys())

    if not categories:
        categories = sorted(path.name for path in examples_dir.iterdir() if path.is_dir())

    tasks: list[dict[str, str]] = []
    for category in categories:
        category_dir = examples_dir / category
        if not category_dir.is_dir():
            logger.warning("Skipping missing category directory: %s", category_dir)
            continue
        files = sorted(category_dir.glob("*.json"))
        if selected_by_list:
            allowed = selected_by_list.get(category, set())
            files = [path for path in files if path.stem in allowed or _task_id_from_path(path) in allowed]
        if task_ids:
            files = [path for path in files if path.stem in task_ids or _task_id_from_path(path) in task_ids]
        if max_per_category:
            files = files[: int(max_per_category)]
        for path in files:
            tasks.append({"category": category, "file_path": str(path), "id": _task_id_from_path(path)})

    if max_total:
        tasks = tasks[: int(max_total)]
    return tasks


def _save_ground_truth(result_dir: Path, score: float, threshold: float) -> Path:
    reward_log = result_dir / "reward_log"
    reward_log.mkdir(parents=True, exist_ok=True)
    path = reward_log / "ground_truth.json"
    path.write_text(
        json.dumps({"score": score, "success": score > threshold}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _save_comparison(evaluation: dict[str, Any], gt_score: float, result_dir: Path, threshold: float, epsilon: float) -> tuple[Path, Path]:
    reward_log = result_dir / "reward_log"
    reward_log.mkdir(parents=True, exist_ok=True)
    evaluation_path = reward_log / "evaluation.json"
    evaluation_path.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False), encoding="utf-8")

    reward = _safe_float(evaluation.get("reward"))
    reward_success = reward is not None and reward > threshold
    gt_success = gt_score > threshold
    strict_equal = reward is not None and abs(reward - gt_score) <= epsilon
    comparison = {
        "reward_agent": {
            "reward": reward,
            "verdict": evaluation.get("verdict"),
            "success_binary": reward_success,
        },
        "ground_truth": {
            "score": gt_score,
            "success_binary": gt_success,
        },
        "match_binary": reward_success == gt_success,
        "match_strict_equal": strict_equal,
        "difference": None if reward is None else abs(reward - gt_score),
    }
    comparison_path = reward_log / "comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    return evaluation_path, comparison_path


def _build_client_config(reward_cfg: dict[str, Any]) -> Optional[dict[str, Any]]:
    client_cfg = reward_cfg.get("client", {}) or {}
    api_key = client_cfg.get("api_key")
    if not api_key and client_cfg.get("api_key_env"):
        api_key = os.getenv(str(client_cfg["api_key_env"]))
    if not api_key:
        api_key = os.getenv("IRA_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("deerapi_key")
    base_url = client_cfg.get("base_url")
    if not base_url and client_cfg.get("base_url_env"):
        base_url = os.getenv(str(client_cfg["base_url_env"]))
    if not base_url:
        base_url = os.getenv("IRA_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if not api_key and not base_url:
        return None
    result = {"type": client_cfg.get("type", reward_cfg.get("client_type", "deerapi"))}
    if api_key:
        result["api_key"] = api_key
    if base_url:
        result["base_url"] = base_url
    return result


def _run_reward_agent(task: dict[str, Any], result_dir: Path, env: Any, config: dict[str, Any], initial_screenshot: Optional[str]) -> dict[str, Any]:
    reward_cfg = config.get("reward_agent", {}) or {}
    from RewardAgent.agent_improved import RewardAgentImproved

    tool_app = _infer_tool_app(task["category"], reward_cfg.get("tool_app", "auto"))
    temperature = reward_cfg.get("temperature", 0.0)
    agent = RewardAgentImproved(
        model_id=reward_cfg.get("model_id", "gpt-4o"),
        env=env,
        app=tool_app,
        max_images=int(reward_cfg.get("max_images", 5)),
        max_steps=int(reward_cfg.get("max_steps", 30)),
        client_config=_build_client_config(reward_cfg),
        client_type=reward_cfg.get("client_type", "deerapi"),
        temperature=None if temperature is None else float(temperature),
    )
    return agent.evaluate(
        task_instruction=task.get("instruction", ""),
        apps=task.get("related_apps", []),
        output_dir=str(result_dir),
        initial_state_screenshot_path=initial_screenshot,
    )


def process_single_task(task_item: dict[str, str], config: dict[str, Any]) -> dict[str, Any]:
    desktop_cfg = config.get("desktop_env", {}) or {}
    replay_cfg = config.get("replay", {}) or {}
    reward_cfg = config.get("reward_agent", {}) or {}
    threshold = float(replay_cfg.get("success_threshold", 0.8))
    epsilon = float(replay_cfg.get("epsilon", 0.0))
    output_root = _resolve_path(replay_cfg.get("output_dir", "runs/parallel_sample_replay"))

    record: dict[str, Any] = {
        "file_path": task_item["file_path"],
        "id": task_item["id"],
        "category": task_item["category"],
        "status": "pending",
        "error": None,
        "output_dir": None,
        "reward_agent_reward": None,
        "ground_truth_score": None,
        "verdict": None,
        "traj_steps": None,
        "eval_steps": None,
        "match_binary": None,
        "match_strict_equal": None,
        "difference": None,
        "evaluation_path": None,
        "comparison_path": None,
    }
    env = None
    try:
        task_json = json.loads(Path(task_item["file_path"]).read_text(encoding="utf-8"))
        task_id = task_json.get("id", task_item["id"])
        record["id"] = task_id
        traj = task_json.get("traj")
        if not isinstance(traj, list) or not traj:
            record["status"] = "skip_no_traj"
            return record
        record["traj_steps"] = len(traj)

        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = output_root / f"replay-{task_id}-{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)
        record["output_dir"] = str(result_dir)

        load_dotenv()
        osworld_token = desktop_cfg.get("token") or os.getenv("OSWORLD_TOKEN")
        if osworld_token:
            os.environ["OSWORLD_TOKEN"] = str(osworld_token)
        osworld_base_url = desktop_cfg.get("base_url") or os.getenv("OSWORLD_BASE_URL")
        if osworld_base_url:
            os.environ["OSWORLD_BASE_URL"] = str(osworld_base_url)

        try:
            from desktop_env.desktop_env import DesktopEnv
        except Exception as exc:
            raise RuntimeError(
                "Could not import desktop_env. Install the compatible Docker desktop environment "
                "from https://github.com/Computer-use-agents/GUI-Docker-Env and ensure it is on PYTHONPATH."
            ) from exc

        env = DesktopEnv(
            action_space=desktop_cfg.get("action_space", "pyautogui"),
            provider_name=desktop_cfg.get("provider_name", "docker_server"),
            os_type=desktop_cfg.get("os_type", "Ubuntu"),
        )
        initial_screenshot = replay_trajectory_only(
            env,
            output_trajectory_dir=result_dir,
            sleep_after_execution=float(desktop_cfg.get("sleep_after_execution", 0.5)),
            reset_wait_seconds=float(desktop_cfg.get("reset_wait_seconds", 60.0)),
            inter_step_wait_seconds=float(desktop_cfg.get("inter_step_wait_seconds", 2.0)),
            traj_data=traj,
            task_config=task_json,
        )

        infeasible = task_json.get("evaluator", {}).get("func") == "infeasible"
        reward_enabled = bool(reward_cfg.get("enabled", True))
        if reward_enabled:
            try:
                evaluation = _run_reward_agent(task_json, result_dir, env, config, initial_screenshot)
            except Exception as exc:
                # Keep the task alive: record the failure and still compare
                # against env.evaluate() (reward -1.0 counts as predicted failure).
                logger.error("Reward agent failed for %s: %s", task_id, exc, exc_info=True)
                record["reward_agent_error"] = str(exc)
                evaluation = {"reward": -1.0, "verdict": "Error", "reasoning": f"Reward agent failed: {exc}"}
            record["reward_agent_reward"] = _safe_float(evaluation.get("reward"))
            record["verdict"] = evaluation.get("verdict")
            record["eval_steps"] = evaluation.get("steps")
        else:
            evaluation = None
            record["verdict"] = "NoRewardAgent"

        gt_score = 0.0 if infeasible else float(env.evaluate())
        record["ground_truth_score"] = gt_score

        if evaluation is None:
            ground_truth_path = _save_ground_truth(result_dir, gt_score, threshold)
            record["comparison_path"] = str(ground_truth_path)
            record["status"] = "ok_no_reward_agent"
        else:
            evaluation_path, comparison_path = _save_comparison(evaluation, gt_score, result_dir, threshold, epsilon)
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
            record["evaluation_path"] = str(evaluation_path)
            record["comparison_path"] = str(comparison_path)
            record["match_binary"] = comparison.get("match_binary")
            record["match_strict_equal"] = comparison.get("match_strict_equal")
            record["difference"] = comparison.get("difference")
            record["status"] = "ok" if record["match_binary"] else "mismatch"
        return record
    except Exception as exc:
        record["status"] = "error"
        record["error"] = f"{exc}\n{traceback.format_exc()}"
        logger.error("Task failed: %s", task_item.get("file_path"), exc_info=True)
        return record
    finally:
        if env is not None:
            try:
                env.close()
            except Exception as exc:
                logger.warning("Failed to close desktop environment: %s", exc)


def save_summary(output_root: Path, records: list[dict[str, Any]], success_threshold: float) -> tuple[Path, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    total = len(records)
    match_binary_count = sum(1 for item in records if item.get("match_binary") is True)
    unknown_count = sum(1 for item in records if item.get("verdict") == "Unknown")
    diffs = [item["difference"] for item in records if item.get("difference") is not None]

    tp = fp = tn = fn = 0
    evaluated = 0
    for item in records:
        if item.get("verdict") == "Unknown":
            continue
        reward = item.get("reward_agent_reward")
        truth = item.get("ground_truth_score")
        if reward is None or truth is None:
            continue
        evaluated += 1
        predicted = float(reward) > success_threshold
        actual = float(truth) > success_threshold
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision is None or recall is None:
        f1 = None
    else:
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    summary = {
        "total": total,
        "status_counts": {status: sum(1 for item in records if item.get("status") == status) for status in sorted({item.get("status") for item in records})},
        "match_binary_count": match_binary_count,
        "match_binary_rate": match_binary_count / total if total else 0.0,
        "avg_difference": sum(diffs) / len(diffs) if diffs else None,
        "classification": {
            "total_evaluated": evaluated,
            "unknown_count": unknown_count,
            "success_threshold": success_threshold,
            "TP": tp,
            "FP": fp,
            "TN": tn,
            "FN": fn,
            "accuracy": (tp + tn) / evaluated if evaluated else None,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "records": records,
    }
    summary_json = output_root / "summary.json"
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    fields = [
        "file_path",
        "id",
        "category",
        "status",
        "error",
        "output_dir",
        "reward_agent_reward",
        "ground_truth_score",
        "difference",
        "verdict",
        "traj_steps",
        "eval_steps",
        "match_binary",
        "match_strict_equal",
        "evaluation_path",
        "comparison_path",
    ]
    summary_csv = output_root / "summary.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in records:
            writer.writerow({field: item.get(field) for field in fields})
    return summary_json, summary_csv


def parallel_sample_replay(config_path: str | Path = DEFAULT_CONFIG, *, dry_run: bool = False) -> list[dict[str, Any]]:
    config = _load_config(config_path)
    _configure_logging((config.get("logging", {}) or {}).get("level", "INFO"))

    replay_cfg = config.get("replay", {}) or {}
    output_root = _resolve_path(replay_cfg.get("output_dir", "runs/parallel_sample_replay"))
    max_workers = int(replay_cfg.get("max_workers", 1))
    skip_existing = bool(replay_cfg.get("skip_existing", True))
    success_threshold = float(replay_cfg.get("success_threshold", 0.8))

    tasks = collect_tasks(config)
    if dry_run:
        logger.info("Dry run: %d task(s) selected.", len(tasks))
        for item in tasks:
            logger.info("  %s %s %s", item["category"], item["id"], item["file_path"])
        return []

    reward_enabled = bool((config.get("reward_agent", {}) or {}).get("enabled", True))
    records: list[dict[str, Any]] = []
    scheduled: list[dict[str, str]] = []
    if skip_existing:
        for item in tasks:
            if _has_complete_run(item["id"], output_root, require_comparison=reward_enabled):
                existing = _load_existing_result(item["id"], output_root) or {}
                existing.update({"file_path": item["file_path"], "category": item["category"], "id": item["id"], "status": "skip_existing", "error": None})
                records.append(existing)
            else:
                scheduled.append(item)
    else:
        scheduled = tasks

    logger.info("Selected %d task(s): %d scheduled, %d skipped.", len(tasks), len(scheduled), len(records))
    if scheduled:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_task, item, config): item for item in scheduled}
            for future in concurrent.futures.as_completed(futures):
                item = futures[future]
                try:
                    record = future.result()
                except Exception as exc:
                    logger.error("Worker crashed for %s: %s", item.get("id"), exc, exc_info=True)
                    record = {
                        "file_path": item.get("file_path"),
                        "category": item.get("category"),
                        "id": item.get("id"),
                        "status": "error",
                        "error": f"worker crashed: {exc}",
                    }
                records.append(record)
                logger.info("Finished %s: %s", record.get("id"), record.get("status"))

    summary_json, summary_csv = save_summary(output_root, records, success_threshold)
    logger.info("summary.json: %s", summary_json)
    logger.info("summary.csv:  %s", summary_csv)
    return records


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay GUI-RewardBench samples in parallel and evaluate with IRA.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to replay YAML config.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and print selected tasks without launching desktop_env.")
    args = parser.parse_args(argv)
    try:
        parallel_sample_replay(args.config, dry_run=args.dry_run)
        return 0
    except Exception as exc:
        logger.exception("parallel_sample_replay failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
