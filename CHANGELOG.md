# Changelog

All notable changes to this project are documented in this file. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4.1] - 2026-05-17

### Added
- `[API]` marker shown in dim gray after the Codex model name when the latest Codex session is running in API key mode (detected by absence of `rate_limits` in the `token_count` event of `~/.codex/sessions/.../*.jsonl`, which also covers cases where no `token_count` event is emitted at all such as `Quota exceeded` responses).
- The marker mirrors the Claude-side convention: subscription users see rate-limit bars as the usage signal, API-key users see `$X.XX` cost on Claude / `[API]` on Codex. The marker text is intentionally generic — no subscription plan proper nouns are emitted from any output string.

### Changed
- Codex side: N/A bars are now omitted individually instead of rendered as empty `N/A` rows. When a bar's value cannot be computed (e.g. `rate_limits` absent in API mode, or `token_count` event missing entirely), that row is simply not shown. Subscription mode with full data continues to render all four rows; API-mode-with-successful-response shows model name + Context; quota-exceeded etc. shows model name only.

### Notes
- Subscription-authenticated Codex sessions keep their existing display unchanged when all data is available. `rate_limits.primary/secondary` bars remain the usage signal.
- Default behavior unchanged: `--codex` opt-in is still required; without it, no Codex-related I/O happens.
- Known limitation under review: the `[API]` detection currently reflects the latest jsonl file, so a stale API-mode session can keep `[API]` showing even after the user switches back to subscription auth until a new session is started. A stricter detection (e.g. mtime-based liveness check or auth-mode-change trigger) is being designed for a follow-up release — see `~/.claude/plans/` for the current discussion.

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
