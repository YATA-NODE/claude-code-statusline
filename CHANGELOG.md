# Changelog

All notable changes to this project are documented in this file. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4.0] - 2026-05-16

### Added
- `--codex` opt-in flag to display Codex CLI usage side-by-side with the existing 4-line layout:
  - Model name (tracks `/model` switches via the latest `turn_context` line, sanitized of ANSI/OSC control sequences and truncated to 32 chars)
  - Context usage % (`total_tokens` ÷ `model_context_window`)
  - 5h primary rate (`rate_limits.primary.used_percent` + `resets_at`)
  - Weekly secondary rate (`rate_limits.secondary.used_percent` + `resets_at`)
- Auto-fallback: the right column is silently hidden when `~/.codex/` is absent, no session jsonl exists for today or yesterday, neither model nor rate-limit info could be extracted, or the terminal is narrower than 120 cells. The existing left-side 4 lines never break.
- Latest session file is selected by `mtime` across **today + yesterday combined** (not biased toward today).
- `--width <N>` and `STATUSLINE_COLUMNS` env to override terminal width (Claude Code's statusLine runner pipes all stdio, so `os.get_terminal_size` usually returns the 80-cell fallback and silently hides the right column without an override).
- Tmux pane width auto-detection: when `$TMUX` is set, `tmux display-message -p '#{pane_width}'` is queried per tick so pane split/unsplit is followed automatically. Tmux pane width is preferred over `--width` because a pane physically caps render width at `pane_width`.
- Full-width / CJK character cell width via `unicodedata.east_asian_width` in `visible_len()`. Lines like `⚠ /compact 推奨` are now measured at their actual cell width (15) instead of code-point count (13), preventing 2-cell overlap with the right Codex column.
- Terminal width resolution (highest first): tmux pane_width → `--width` → `STATUSLINE_COLUMNS` → `COLUMNS` → `stderr`/`stdout`/`stdin` TTY fd → `shutil.get_terminal_size` fallback (80).

### Notes
- Default OFF — fully backward compatible. Without `--codex`, no Codex-related I/O happens.
- Read-only access to `~/.codex/sessions/YYYY/MM/DD/*.jsonl`. Nothing is written back.
- Still standard library only (added `argparse`, `glob`, `re`, `shutil`, `itertools.zip_longest`, `datetime`).

## [0.3.1]

### Fixed
- Keep cost hidden after `/compact` for subscription users (two-step subscription detection via `~/.cache/claude-code-statusline/<session_id>.subscription` marker).

## [0.3.0]

### Added
- Show `repo/branch` to the right of the model name (via `git rev-parse`).
- Show accumulated API cost `$X.XX` on the first line for API-key users only (hidden for subscription users).

## [0.2.x]

### Added
- Show next reset time (`↻ HH:MM` / `↻ M/D HH:MM`, local timezone) at the right end of the 5h / Week bars.

## [0.1.x]

### Added
- Initial release: 4-line layout (model name + Context / 5h / Week bars), stage colors (green / yellow / red), `⚠ /compact 推奨` when Context ≥ 80%.
