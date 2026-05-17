# Changelog

All notable changes to this project are documented in this file. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [0.4.3] - 2026-05-17

### Changed
- Codex side: when the most-recent jsonl has no `token_count` event (e.g. quota-exceeded with no response), the extractor now **falls back to earlier jsonl files** (today + yesterday, mtime-desc order) until one with a `token_count` event is found. Rate-limit bars and Context now display the **last known state** instead of `N/A`, so subscription users can check "how much budget is left" before starting a new Codex session.
- Model name is taken from the first `turn_context` encountered during the same walk (so the most-recent session's model is shown even if its budget came from an earlier jsonl).

### Notes
- Falls back to the existing behavior (no row rendered) if no jsonl in today + yesterday has a `token_count` event at all.
- Still subject to the `--codex` opt-in; no Codex I/O without it.
- Per-tick cost: at most a handful of jsonl reads (today + yesterday window), short-circuited once both `model` and `token_count` are found. In practice the very first or second file already has both fields.

## [0.4.2] - 2026-05-17

### Fixed
- Codex side: N/A bar omission is now **limited to API mode only**. Subscription-authenticated sessions keep N/A bars visible (Context / 5h / Week rows always render, with `N/A` when a value cannot be computed) because the bars and their reset times are decision info for the user — "how much 5h budget is left, when does the weekly window reset" matters even when a single tick is briefly missing data. API mode (usage-based billing) continues to hide N/A rows since rate limits aren't a concept there.
- Restores the v0.4.0-style Codex 4-row display for subscription users whose latest jsonl temporarily lacks `token_count` (e.g. a stale API-mode jsonl is the most recent file, while `auth.json` shows the user is back on subscription).

## [0.4.1] - 2026-05-17

### Added
- `[API]` marker shown in dim gray after the Codex model name when Codex is currently using API key authentication. Detection reads `~/.codex/auth.json`'s `OPENAI_API_KEY` field — only its existence and length are checked, never the key value itself — so the marker reflects the **live auth state** rather than relying on stale jsonl history. Auth switches (`codex login --with-api-key` ↔ `codex login`) are picked up on the next statusline refresh (within 60s) regardless of whether a new Codex session has been started.
- The marker mirrors the Claude-side convention: subscription users see rate-limit bars as the usage signal, API-key users see `$X.XX` cost on Claude / `[API]` on Codex. The marker text is intentionally generic — no subscription plan proper nouns are emitted from any output string.

### Changed
- Codex side: N/A bars are now omitted individually instead of rendered as empty `N/A` rows. When a bar's value cannot be computed (e.g. `rate_limits` absent in API mode, or `token_count` event missing entirely), that row is simply not shown. Subscription mode with full data continues to render all four rows; API-mode-with-successful-response shows model name + Context; quota-exceeded etc. shows model name only.

### Notes
- Subscription-authenticated Codex sessions keep their existing display unchanged when all data is available. `rate_limits.primary/secondary` bars remain the usage signal.
- Default behavior unchanged: `--codex` opt-in is still required; without it, no Codex-related I/O happens.
- `~/.codex/auth.json` access is read-only and fails safe (no `[API]` shown) on any read error / JSON parse error / missing field. The key string content is never read into a variable used for output, comparison, or logging — only `isinstance(key, str) and len(key) > 0` is evaluated.

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
