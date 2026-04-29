#!/usr/bin/env python3
"""Claude Code Status Line: model name + context/5h/week usage bars."""
import json
import sys

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

    lines = [f"{BOLD}{model_name}{RESET}"]
    for label, pct in (("Context", ctx), ("5h", five), ("Week", week)):
        line = render_bar(label, pct)
        if label == "Context" and pct >= 80:
            line += f"  \033[1;31m⚠ /compact 推奨\033[0m"
        lines.append(line)

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
