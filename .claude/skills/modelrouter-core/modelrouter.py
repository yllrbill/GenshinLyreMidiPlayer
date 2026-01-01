#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modelrouter Core - 复杂度分析 + 使用追踪

核心功能:
1. 分析 prompt 复杂度 (EASY/MEDIUM/HARD)
2. 给出模型建议 (haiku/sonnet/opus)
3. 追踪使用记录
4. 生成统计报告

注意: 用户使用订阅计划，模型切换不可能。此脚本只做分析和追踪。

Usage:
    python modelrouter.py status              # 显示当前会话统计
    python modelrouter.py analyze "prompt"    # 分析复杂度
    python modelrouter.py stats [day|week]    # 周期统计
    python modelrouter.py track "prompt" model  # 记录使用
"""

import os
import sys
import re
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
STATE_DIR = Path(__file__).parent.parent.parent / "state" / "modelrouter"
PATTERNS_FILE = SCRIPT_DIR / "patterns.yaml"

# Ensure state directories exist
STATE_DIR.mkdir(parents=True, exist_ok=True)
(STATE_DIR / "history").mkdir(exist_ok=True)
(STATE_DIR / "aggregates").mkdir(exist_ok=True)


# ============================================================================
# Pattern Loading
# ============================================================================

def load_patterns() -> dict:
    """Load complexity detection patterns from patterns.yaml."""
    if not PATTERNS_FILE.exists():
        return {
            "hard_keywords": [],
            "medium_keywords": [],
            "easy_indicators": [],
            "thresholds": {"hard": 50, "medium": 25, "easy": 0},
            "context_weights": {"length": {"short": 0, "medium": 10, "long": 20}},
            "model_mapping": {"HARD": "opus", "MEDIUM": "sonnet", "EASY": "haiku"}
        }

    with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================================
# Complexity Analysis
# ============================================================================

def analyze_prompt(prompt: str, context_files: int = 0) -> dict:
    """
    Analyze prompt complexity and return scoring details.

    Args:
        prompt: The user prompt to analyze
        context_files: Number of context files (for context score)

    Returns:
        dict with score, level, model, and reasoning
    """
    patterns = load_patterns()

    total_score = 0
    matches = []

    # 1. Keyword matching
    for kw in patterns.get("hard_keywords", []):
        pattern = kw.get("pattern", "")
        weight = kw.get("weight", 0)
        category = kw.get("category", "unknown")

        if re.search(pattern, prompt):
            total_score += weight
            matches.append({
                "pattern": pattern,
                "weight": weight,
                "category": category,
                "type": "hard"
            })

    for kw in patterns.get("medium_keywords", []):
        pattern = kw.get("pattern", "")
        weight = kw.get("weight", 0)
        category = kw.get("category", "unknown")

        if re.search(pattern, prompt):
            total_score += weight
            matches.append({
                "pattern": pattern,
                "weight": weight,
                "category": category,
                "type": "medium"
            })

    for kw in patterns.get("easy_indicators", []):
        pattern = kw.get("pattern", "")
        weight = kw.get("weight", 0)  # Usually negative
        category = kw.get("category", "unknown")

        if re.search(pattern, prompt):
            total_score += weight
            matches.append({
                "pattern": pattern,
                "weight": weight,
                "category": category,
                "type": "easy"
            })

    # 2. Length score
    length_weights = patterns.get("context_weights", {}).get("length", {})
    prompt_len = len(prompt)

    if prompt_len > 500:
        length_score = length_weights.get("long", 20)
    elif prompt_len > 200:
        length_score = length_weights.get("medium", 10)
    else:
        length_score = length_weights.get("short", 0)

    total_score += length_score

    # 3. Context score
    files_weights = patterns.get("context_weights", {}).get("files", {})

    if context_files >= 5:
        context_score = files_weights.get("many", 20)
    elif context_files >= 2:
        context_score = files_weights.get("some", 10)
    else:
        context_score = files_weights.get("few", 0)

    total_score += context_score

    # 4. Determine level and model
    thresholds = patterns.get("thresholds", {"hard": 50, "medium": 25})
    model_mapping = patterns.get("model_mapping", {
        "HARD": "opus",
        "MEDIUM": "sonnet",
        "EASY": "haiku"
    })

    if total_score >= thresholds.get("hard", 50):
        level = "HARD"
    elif total_score >= thresholds.get("medium", 25):
        level = "MEDIUM"
    else:
        level = "EASY"

    model = model_mapping.get(level, "sonnet")

    return {
        "score": total_score,
        "level": level,
        "model": model,
        "reasoning": {
            "keyword_matches": matches,
            "length_score": length_score,
            "context_score": context_score,
            "prompt_length": prompt_len,
            "context_files": context_files
        }
    }


# ============================================================================
# State Management
# ============================================================================

def get_session_file() -> Path:
    """Get the session.latest.yaml file path."""
    return STATE_DIR / "session.latest.yaml"


def load_session() -> dict:
    """Load current session state."""
    session_file = get_session_file()

    if not session_file.exists():
        return {
            "envelope": {
                "command": "modelrouter",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "OK",
                "error_code": None,
            },
            "session": {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "project_dir": str(Path.cwd())
            },
            "tasks": [],
            "summary": {
                "total_tasks": 0,
                "models_used": {"haiku": 0, "sonnet": 0, "opus": 0},
                "complexity_distribution": {"EASY": 0, "MEDIUM": 0, "HARD": 0}
            }
        }

    with open(session_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_session(data: dict):
    """Save session state."""
    data["envelope"]["timestamp"] = datetime.now(timezone.utc).isoformat()

    session_file = get_session_file()
    with open(session_file, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def track_usage(prompt: str, model: str, analysis: dict = None):
    """
    Record a usage entry.

    Args:
        prompt: The prompt that was analyzed
        model: The model that was/would be used
        analysis: Optional analysis result
    """
    session = load_session()

    if analysis is None:
        analysis = analyze_prompt(prompt)

    task_id = f"T-{datetime.now().strftime('%y%m%d')}-{len(session.get('tasks', [])) + 1:04d}"

    task_entry = {
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
        "complexity": {
            "level": analysis["level"],
            "score": analysis["score"]
        },
        "model": {
            "suggested": analysis["model"],
            "actual": model,
            "override": model != analysis["model"]
        }
    }

    # Update session
    if "tasks" not in session:
        session["tasks"] = []
    session["tasks"].append(task_entry)

    # Update summary
    if "summary" not in session:
        session["summary"] = {
            "total_tasks": 0,
            "models_used": {"haiku": 0, "sonnet": 0, "opus": 0},
            "complexity_distribution": {"EASY": 0, "MEDIUM": 0, "HARD": 0}
        }

    session["summary"]["total_tasks"] += 1
    session["summary"]["models_used"][model] = session["summary"]["models_used"].get(model, 0) + 1
    session["summary"]["complexity_distribution"][analysis["level"]] += 1

    save_session(session)

    # Also save to history
    save_to_history(task_entry)

    return task_entry


def save_to_history(task_entry: dict):
    """Save task entry to history directory."""
    today = datetime.now().strftime("%Y%m%d")
    history_dir = STATE_DIR / "history" / today
    history_dir.mkdir(parents=True, exist_ok=True)

    history_file = history_dir / f"{task_entry['task_id']}.yaml"
    with open(history_file, "w", encoding="utf-8") as f:
        yaml.dump(task_entry, f, allow_unicode=True, default_flow_style=False)


# ============================================================================
# CLI Commands
# ============================================================================

def cmd_status():
    """Display current session status."""
    session = load_session()

    print("envelope:")
    print(f"  command: modelrouter")
    print(f"  timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"  status: OK")
    print()

    summary = session.get("summary", {})
    print(f"Session: {session.get('session', {}).get('started_at', 'N/A')}")
    print(f"Tasks: {summary.get('total_tasks', 0)}")

    models = summary.get("models_used", {})
    print(f"Models: haiku({models.get('haiku', 0)}) sonnet({models.get('sonnet', 0)}) opus({models.get('opus', 0)})")

    complexity = summary.get("complexity_distribution", {})
    print(f"Complexity: EASY({complexity.get('EASY', 0)}) MEDIUM({complexity.get('MEDIUM', 0)}) HARD({complexity.get('HARD', 0)})")

    # Show recent tasks
    tasks = session.get("tasks", [])[-5:]
    if tasks:
        print()
        print("Recent Tasks:")
        for task in reversed(tasks):
            level = task.get("complexity", {}).get("level", "?")
            model = task.get("model", {}).get("actual", "?")
            preview = task.get("prompt_preview", "")[:50]
            print(f"  [{level}→{model}] {preview}...")


def cmd_analyze(prompt: str, context_files: int = 0):
    """Analyze prompt complexity."""
    analysis = analyze_prompt(prompt, context_files)

    print("envelope:")
    print(f"  command: modelrouter")
    print(f"  timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"  status: OK")
    print()
    print(f"Prompt: \"{prompt[:80]}{'...' if len(prompt) > 80 else ''}\"")
    print()
    print("Analysis:")

    for match in analysis["reasoning"]["keyword_matches"]:
        sign = "+" if match["weight"] > 0 else ""
        print(f"  - \"{match['pattern']}\" ({sign}{match['weight']}, {match['category']})")

    print(f"  Length: {analysis['reasoning']['prompt_length']} chars (+{analysis['reasoning']['length_score']})")
    print(f"  Context: {analysis['reasoning']['context_files']} files (+{analysis['reasoning']['context_score']})")
    print("  ---")
    print(f"  Total Score: {analysis['score']}")
    print(f"  Level: {analysis['level']}")
    print(f"  Model: {analysis['model']}")


def cmd_track(prompt: str, model: str):
    """Record a usage entry."""
    entry = track_usage(prompt, model)
    print(f"Tracked: {entry['task_id']}")
    print(f"  Level: {entry['complexity']['level']}")
    print(f"  Score: {entry['complexity']['score']}")
    print(f"  Suggested: {entry['model']['suggested']}")
    print(f"  Actual: {entry['model']['actual']}")
    print(f"  Override: {entry['model']['override']}")


def cmd_stats(period: str = "day"):
    """Show statistics for a period."""
    session = load_session()
    summary = session.get("summary", {})

    print(f"Period: {period}")
    print(f"Total Tasks: {summary.get('total_tasks', 0)}")
    print()
    print("Models Used:")

    models = summary.get("models_used", {})
    total = sum(models.values()) or 1
    for model, count in models.items():
        pct = count / total * 100
        print(f"  {model}: {count} ({pct:.1f}%)")

    print()
    print("Complexity Distribution:")
    complexity = summary.get("complexity_distribution", {})
    for level, count in complexity.items():
        pct = count / total * 100
        print(f"  {level}: {count} ({pct:.1f}%)")


# ============================================================================
# Main
# ============================================================================

def print_usage():
    """Print usage information."""
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_status()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "status":
        cmd_status()

    elif command == "analyze":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: modelrouter.py analyze \"prompt\"")
            sys.exit(1)
        prompt = sys.argv[2]
        context_files = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        cmd_analyze(prompt, context_files)

    elif command == "track":
        if len(sys.argv) < 4:
            print("[ERROR] Usage: modelrouter.py track \"prompt\" model")
            sys.exit(1)
        prompt = sys.argv[2]
        model = sys.argv[3]
        cmd_track(prompt, model)

    elif command == "stats":
        period = sys.argv[2] if len(sys.argv) > 2 else "day"
        cmd_stats(period)

    elif command in ("-h", "--help", "help"):
        print_usage()

    else:
        print(f"[ERROR] Unknown command: {command}")
        print_usage()
        sys.exit(1)
