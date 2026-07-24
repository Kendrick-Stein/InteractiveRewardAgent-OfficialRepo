"""Config-driven replay utilities for Interactive Reward Agent."""

from __future__ import annotations

from typing import Any

__all__ = ["parallel_sample_replay", "replay_trajectory_only"]


def __getattr__(name: str) -> Any:
    if name == "parallel_sample_replay":
        from .parallel_sample_replay import parallel_sample_replay

        return parallel_sample_replay
    if name == "replay_trajectory_only":
        from .replay_utils import replay_trajectory_only

        return replay_trajectory_only
    raise AttributeError(name)
