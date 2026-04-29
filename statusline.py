#!/usr/bin/env python3
"""Claude Code Status Line: model name + context/5h/week usage bars."""
import json
import sys
import time

BAR_WIDTH = 24
LABEL_WIDTH = 9
FILL_CHAR = "▆"   # ▆ lower three quarters block
EMPTY_CHAR = "▆"  # 同じ形で色だけ薄くして輪郭を揃える

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
EMPTY_COLOR = "\033[38;5;238m"  # 暗いグレー (xterm-256)


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


def get_epoch(data: dict, *path: str):
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


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    model_obj = data.get("model") or {}
    model_name = model_obj.get("display_name") or model_obj.get("id") or "Unknown"

    ctx = get_pct(data, "context_window", "used_percentage")
    five = get_pct(data, "rate_limits", "five_hour", "used_percentage")
    week = get_pct(data, "rate_limits", "seven_day", "used_percentage")
    five_reset = get_epoch(data, "rate_limits", "five_hour", "resets_at")
    week_reset = get_epoch(data, "rate_limits", "seven_day", "resets_at")

    lines = [f"{BOLD}{model_name}{RESET}"]
    for label, pct in (("Context", ctx), ("5h", five), ("Week", week)):
        line = render_bar(label, pct)
        if label == "Context" and pct >= 80:
            line += f"  \033[1;31m⚠ /compact 推奨\033[0m"
        elif label == "5h" and pct >= 0 and five_reset is not None:
            line += f"  {DIM}↻ {format_reset(five_reset, False)}{RESET}"
        elif label == "Week" and pct >= 0 and week_reset is not None:
            line += f"  {DIM}↻ {format_reset(week_reset, True)}{RESET}"
        lines.append(line)

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
