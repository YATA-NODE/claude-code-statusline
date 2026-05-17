#!/usr/bin/env python3
"""Claude Code Status Line: model name + context/5h/week usage bars."""
import argparse
import datetime as _dt
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from itertools import zip_longest

__version__ = "0.4.2"

CACHE_DIR = os.path.expanduser("~/.cache/claude-code-statusline")

BAR_WIDTH = 24
LABEL_WIDTH = 9
FILL_CHAR = "▆"   # ▆ lower three quarters block
EMPTY_CHAR = "▆"  # 同じ形で色だけ薄くして輪郭を揃える

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
EMPTY_COLOR = "\033[38;5;238m"  # 暗いグレー (xterm-256)

SEP = "  "
TWO_COL_MIN_WIDTH = 120
CODEX_DIR = os.path.expanduser("~/.codex")
CODEX_AUTH = os.path.expanduser("~/.codex/auth.json")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
OSC_RE = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)", re.DOTALL)
CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
MODEL_NAME_MAX = 32


def color_for(pct: int) -> str:
    if pct < 0:
        return "\033[90m"
    if pct < 60:
        return "\033[32m"
    if pct < 80:
        return "\033[33m"
    return "\033[31m"


def get_pct(data: dict, *path: str) -> int:
    cur = data
    for key in path:
        if not isinstance(cur, dict) or cur.get(key) is None:
            return -1
        cur = cur[key]
    if isinstance(cur, bool):
        return -1
    if isinstance(cur, (int, float)):
        return max(0, min(100, int(cur)))
    return -1


def get_int(data: dict, *path: str):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or cur.get(key) is None:
            return None
        cur = cur[key]
    if isinstance(cur, bool):
        return None
    if isinstance(cur, (int, float)):
        return int(cur)
    return None


def format_reset(epoch: int, with_date: bool) -> str:
    lt = time.localtime(epoch)
    hm = time.strftime("%H:%M", lt)
    if with_date:
        return f"{lt.tm_mon}/{lt.tm_mday} {hm}"
    return hm


def subscription_marker_path(session_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:128]
    return os.path.join(CACHE_DIR, f"{safe}.subscription")


def remember_subscription(session_id: str) -> None:
    if not session_id:
        return
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        open(subscription_marker_path(session_id), "a").close()
    except OSError:
        pass


def is_known_subscription(session_id: str) -> bool:
    if not session_id:
        return False
    try:
        return os.path.exists(subscription_marker_path(session_id))
    except OSError:
        return False


def get_repo_branch(project_dir: str) -> str:
    if not project_dir:
        return ""
    repo = os.path.basename(project_dir.rstrip("/")) or project_dir
    try:
        r = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=1,
        )
        if r.returncode == 0:
            ref = r.stdout.strip()
            if ref and ref != "HEAD":
                return f"{repo} / {ref}"
            if ref == "HEAD":
                r2 = subprocess.run(
                    ["git", "-C", project_dir, "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, timeout=1,
                )
                sha = r2.stdout.strip() if r2.returncode == 0 else ""
                if sha:
                    return f"{repo} / {sha}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return repo


def render_bar(label: str, pct: int) -> str:
    if pct < 0:
        bar = f"{EMPTY_COLOR}{EMPTY_CHAR * BAR_WIDTH}{RESET}"
        return f"{label:<{LABEL_WIDTH}}{bar}  {DIM}N/A{RESET}"
    c = color_for(pct)
    fill = (pct * BAR_WIDTH) // 100
    fill = max(0, min(BAR_WIDTH, fill))
    fill_part = f"{c}{FILL_CHAR * fill}{RESET}"
    empty_part = f"{EMPTY_COLOR}{EMPTY_CHAR * (BAR_WIDTH - fill)}{RESET}"
    return f"{label:<{LABEL_WIDTH}}{fill_part}{empty_part}  {pct:>3d}%"


def visible_len(s: str) -> int:
    s = ANSI_RE.sub("", s)
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def pad_visible(s: str, width: int) -> str:
    return s + " " * max(0, width - visible_len(s))


def sanitize_display(s, limit: int = MODEL_NAME_MAX) -> str:
    if not isinstance(s, str):
        return ""
    s = ANSI_RE.sub("", s)
    s = OSC_RE.sub("", s)
    s = CTRL_RE.sub("", s)
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


# --- Codex (opt-in) ---


def _codex_auth_is_api():
    # Reads only the OPENAI_API_KEY field's existence + length, never the
    # string content. Fail-safe: any error returns False so [API] is not shown
    # on uncertain state. ~/.codex/auth.json is the live source-of-truth for
    # auth mode; latest jsonl mtime could be stale after auth switch.
    try:
        with open(CODEX_AUTH, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError, TypeError):
        return False
    if not isinstance(d, dict):
        return False
    key = d.get("OPENAI_API_KEY")
    return isinstance(key, str) and len(key) > 0


def _codex_latest_jsonl():
    if not os.path.isdir(CODEX_DIR):
        return None
    today = _dt.date.today()
    candidates = []
    for delta in (0, 1):
        d = today - _dt.timedelta(days=delta)
        pattern = os.path.join(
            CODEX_DIR, "sessions",
            f"{d.year:04d}", f"{d.month:02d}", f"{d.day:02d}", "*.jsonl",
        )
        candidates.extend(glob.glob(pattern))
    if not candidates:
        return None
    try:
        return max(candidates, key=os.path.getmtime)
    except OSError:
        return None


def _codex_extract(path):
    model = None
    tc = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if '"turn_context"' in line:
                    try:
                        d = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if d.get("type") == "turn_context":
                        m = (d.get("payload") or {}).get("model")
                        if isinstance(m, str) and m:
                            model = m
                elif '"token_count"' in line:
                    try:
                        d = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    payload = d.get("payload") or {}
                    if d.get("type") == "event_msg" and payload.get("type") == "token_count":
                        tc = payload
    except OSError:
        return None

    if model is None and tc is None:
        return None

    info = {
        "model": model,
        "ctx_pct": -1,
        "five_pct": -1,
        "five_reset": None,
        "week_pct": -1,
        "week_reset": None,
        "is_api_mode": (model is not None) and _codex_auth_is_api(),
    }
    if tc:
        info["five_pct"] = get_pct(tc, "rate_limits", "primary", "used_percent")
        info["five_reset"] = get_int(tc, "rate_limits", "primary", "resets_at")
        info["week_pct"] = get_pct(tc, "rate_limits", "secondary", "used_percent")
        info["week_reset"] = get_int(tc, "rate_limits", "secondary", "resets_at")
        total = get_int(tc, "info", "total_token_usage", "total_tokens")
        ctx_window = get_int(tc, "info", "model_context_window")
        if total is not None and ctx_window is not None and ctx_window > 0:
            info["ctx_pct"] = max(0, min(100, int(total * 100 / ctx_window)))
    return info


def _codex_render(info):
    safe_model = sanitize_display(info["model"]) or "codex"
    header = f"{BOLD}{safe_model}{RESET}"
    if info.get("is_api_mode"):
        header += f"  {DIM}[API]{RESET}"
    lines = [header]
    is_api = info.get("is_api_mode")
    for label, pct, reset_epoch, with_date in (
        ("Context", info["ctx_pct"], None, False),
        ("5h", info["five_pct"], info["five_reset"], False),
        ("Week", info["week_pct"], info["week_reset"], True),
    ):
        # Subscription auth: keep N/A rows visible — rate-limit bars and
        # reset times are decision info for the user (when can I use Codex
        # again?). API auth: hide N/A rows since rate limits are not a
        # concept (usage-based billing instead).
        if is_api and pct < 0:
            continue
        line = render_bar(label, pct)
        if reset_epoch is not None:
            line += f"  {DIM}↻ {format_reset(reset_epoch, with_date)}{RESET}"
        lines.append(line)
    return lines


def _tmux_pane_width():
    if not os.environ.get("TMUX"):
        return None
    try:
        r = subprocess.run(
            ["tmux", "display-message", "-p", "#{pane_width}"],
            capture_output=True, text=True, timeout=0.5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    w = r.stdout.strip()
    return int(w) if w.isdigit() and int(w) > 0 else None


def _term_width(override=None):
    # Inside tmux, pane_width is the only authoritative width:
    # --width or env values would overflow the pane and force wrapping.
    tmux_w = _tmux_pane_width()
    if tmux_w is not None:
        return tmux_w
    if isinstance(override, int) and override > 0:
        return override
    v = os.environ.get("STATUSLINE_COLUMNS") or os.environ.get("COLUMNS")
    if v and v.isdigit() and int(v) > 0:
        return int(v)
    for stream in (sys.stderr, sys.stdout, sys.stdin):
        try:
            cols = os.get_terminal_size(stream.fileno()).columns
            if cols > 0:
                return cols
        except (OSError, AttributeError, ValueError):
            continue
    return shutil.get_terminal_size((80, 24)).columns


def _combine_columns(left_lines, right_lines, width_override=None):
    if not right_lines:
        return left_lines
    term_w = _term_width(width_override)
    if term_w < TWO_COL_MIN_WIDTH:
        return left_lines
    left_w = max((visible_len(l) for l in left_lines), default=0)
    right_w = max((visible_len(r) for r in right_lines), default=0)
    if left_w + len(SEP) + right_w > term_w:
        return left_lines
    combined = []
    for l, r in zip_longest(left_lines, right_lines, fillvalue=""):
        combined.append(pad_visible(l, left_w) + SEP + r)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--codex", action="store_true")
    parser.add_argument("--width", type=int, default=None)
    args, _unknown = parser.parse_known_args()

    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    model_obj = data.get("model") or {}
    model_name = model_obj.get("display_name") or model_obj.get("id") or "Unknown"

    workspace = data.get("workspace") or {}
    project_dir = workspace.get("project_dir") or workspace.get("current_dir") or ""
    repo_branch = get_repo_branch(project_dir)

    session_id = data.get("session_id") or ""

    cost = data.get("cost") or {}
    total_cost = cost.get("total_cost_usd")
    rate_limits_obj = data.get("rate_limits")
    if rate_limits_obj is not None:
        remember_subscription(session_id)
    cost_str = ""
    subscription_known = rate_limits_obj is not None or is_known_subscription(session_id)
    if not subscription_known and isinstance(total_cost, (int, float)) and total_cost > 0:
        cost_str = f"${total_cost:.2f}"

    ctx = get_pct(data, "context_window", "used_percentage")
    five = get_pct(data, "rate_limits", "five_hour", "used_percentage")
    week = get_pct(data, "rate_limits", "seven_day", "used_percentage")
    five_reset = get_int(data, "rate_limits", "five_hour", "resets_at")
    week_reset = get_int(data, "rate_limits", "seven_day", "resets_at")

    header = f"{BOLD}{model_name}{RESET}"
    if repo_branch:
        header += f"  {repo_branch}"
    if cost_str:
        header += f"  {DIM}{cost_str}{RESET}"
    lines = [header]
    for label, pct in (("Context", ctx), ("5h", five), ("Week", week)):
        line = render_bar(label, pct)
        if label == "Context" and pct >= 80:
            line += f"  \033[1;31m⚠ /compact 推奨\033[0m"
        elif label == "5h" and pct >= 0 and five_reset is not None:
            line += f"  {DIM}↻ {format_reset(five_reset, False)}{RESET}"
        elif label == "Week" and pct >= 0 and week_reset is not None:
            line += f"  {DIM}↻ {format_reset(week_reset, True)}{RESET}"
        lines.append(line)

    if args.codex:
        codex_path = _codex_latest_jsonl()
        codex_info = _codex_extract(codex_path) if codex_path else None
        codex_lines = _codex_render(codex_info) if codex_info else []
        lines = _combine_columns(lines, codex_lines, width_override=args.width)

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
