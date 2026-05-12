# claude-code-statusline

Claude Code 用のシンプルな Status Line。**モデル名・コンテキスト窓・5時間レートリミット・週次レートリミット**を、緑/黄/赤の段階色つきバーで入力欄の直下に常時表示します。

![preview](preview.png)

## 特徴

- 4 行のコンパクトな表示（モデル名 + バー 3本）
- バーは下 3/4 ブロック (`▆`) で太く・行間に隙間
- **段階色**: 〜59% 緑 / 60〜79% 黄 / 80%〜 赤
- **コンテキスト 80% 以上で `⚠ /compact 推奨` を末尾に表示**
- **5h / Week バーの末尾に次回リセット時刻 (`↻ HH:MM` / `↻ M/D HH:MM`) をローカル時刻で表示**
- **モデル名の右に `repo名/branch名` を表示**（Git リポジトリ内のとき）
- **API 利用時のみ累計コスト `$X.XX` を末尾に表示**（サブスクリプション利用時は非表示）
- レートリミット情報が無いとき（非サブスク・初回起動直後など）は `N/A` でフォールバック
- 標準ライブラリのみ（外部依存なし）

## 表示内容

| 行 | 内容 | データソース |
|----|------|----|
| 1 | モデル名（太字）+ `repo名/branch名` + `$コスト`（API利用時のみ） | `model.display_name` / `workspace.project_dir` + `git rev-parse` / `cost.total_cost_usd` |
| 2 | Context バー + % | `context_window.used_percentage` |
| 3 | 5h バー + % + ↻ リセット時刻 | `rate_limits.five_hour.used_percentage` / `.resets_at` |
| 4 | Week バー + % + ↻ リセット時刻 | `rate_limits.seven_day.used_percentage` / `.resets_at` |

5h / Week は Claude Code から渡される値をそのまま使うため、**サブスクリプションの実際の残量と一致**します。値が無いときは自動で `N/A` 表示にフォールバックします。

`resets_at` は Unix epoch 秒で渡されるため、本スクリプトは **ローカルタイムゾーンに変換** して表示します。5h は当日内に必ず収まるため `HH:MM` のみ、Week は数日先まで延びるため `M/D HH:MM` 形式で表示します。`resets_at` だけが欠けている場合は時刻表記を省略し、% のみ表示します。

リポジトリ名は `workspace.project_dir` の basename、ブランチ名は `git rev-parse --abbrev-ref HEAD`（detached HEAD 時は短縮 SHA にフォールバック）から取得します。Git リポジトリ外ではディレクトリ名のみを表示します。

コスト表示は **API キー利用が確実なとき**（= サブスクリプション判定が成立しないとき）のみ出ます。判定は次の二段です:

1. 現在の JSON に `rate_limits` があれば即サブスク扱い
2. 過去に同 `session_id` で一度でも `rate_limits` を観測していればサブスク扱い（`~/.cache/claude-code-statusline/<session_id>.subscription` に空ファイルで記録）

この二段判定により、`/compact` 直後など `rate_limits` が一時的に欠落するフレームでもサブスク利用者にコストが漏れません。マーカーは 0 バイトの空ファイルで、不要になったら `~/.cache/claude-code-statusline/` ごと削除して問題ありません。

## 必要環境

- Claude Code
- Python 3.8 以上
- 256 色対応の等幅フォントを表示できるターミナル（Windows Terminal / VS Code 統合ターミナル / Alacritty / iTerm2 など最近のものはほぼ対応）

## インストール

### 1. スクリプトを配置

**方法A: 1ファイルだけ取得（最速・推奨）**

```bash
curl -L https://raw.githubusercontent.com/YATA-NODE/claude-code-statusline/main/statusline.py -o ~/.claude/statusline.py
```

**方法B: clone してからコピー**

```bash
git clone https://github.com/YATA-NODE/claude-code-statusline.git
cp claude-code-statusline/statusline.py ~/.claude/statusline.py
```

### 2. `~/.claude/settings.json` に `statusLine` を追記

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /home/<your-user>/.claude/statusline.py",
    "padding": 0,
    "refreshInterval": 60000
  }
}
```

`/home/<your-user>/` の部分は実際のホームディレクトリ絶対パスに置き換えてください。`~` は展開されないので注意。

### 3. Claude Code を再起動

```bash
/exit
claude --continue
```

## カスタマイズ

`statusline.py` の冒頭に主要な定数があります。書き換えるだけで挙動を変えられます。

| 定数 | デフォルト | 用途 |
|------|----------|------|
| `BAR_WIDTH` | `24` | バーの横幅（セル数） |
| `LABEL_WIDTH` | `9` | 左側ラベルの最小幅 |
| `FILL_CHAR` | `▆` | 埋めセル（下3/4ブロック） |
| `EMPTY_CHAR` | `▆` | 空セル（同形・色のみ違う） |
| `EMPTY_COLOR` | `\033[38;5;238m` | 空セルの色（xterm-256 の暗いグレー） |

### 段階色の閾値を変える

`color_for()` 内の `60` / `80` を変更：

```python
def color_for(pct: int) -> str:
    if pct < 0:    return "\033[90m"
    if pct < 60:   return "\033[32m"   # ← 緑の上限
    if pct < 80:   return "\033[33m"   # ← 黄の上限
    return "\033[31m"
```

### `/compact` 推奨警告の閾値を変える

`main()` 内の `80` を変更：

```python
if label == "Context" and pct >= 80:
    line += f"  \033[1;31m⚠ /compact 推奨\033[0m"
```

### 256 色非対応の端末で空セルが表示されない場合

`EMPTY_COLOR` を 16 色互換に変更：

```python
EMPTY_COLOR = "\033[90m"   # bright black (16色)
```

## 動作の仕組み

Claude Code は `statusLine.command` で指定されたシェルコマンドを定期的に実行し、その標準出力を入力欄の下に表示します。stdin からは現在のセッション情報が JSON で渡されます（`model`, `context_window`, `rate_limits`, `cost`, `workspace`, `transcript_path` 等）。本スクリプトは `model` / `workspace` / `cost` / `context_window` / `rate_limits` を読み取り、必要に応じて `git rev-parse` を 1 回呼んでブランチ名を取得します。

## ライセンス

MIT License — 詳細は [LICENSE](LICENSE) を参照してください。

---

# claude-code-statusline (English)

A simple Status Line for [Claude Code](https://claude.com/claude-code) that displays the **model name, context window usage, 5-hour rate limit, and 7-day rate limit** as color-graded bars (green / yellow / red) right under the input prompt.

![preview](preview.png)

## Features

- Compact 4-line layout (model name + 3 bars)
- Bars use the lower-three-quarters block (`▆`) for visual weight with breathing room between rows
- **Stage colors**: 0–59% green / 60–79% yellow / 80%+ red
- **Shows `⚠ /compact 推奨` next to the Context bar when context usage reaches 80%**
- **Shows the next reset time (`↻ HH:MM` / `↻ M/D HH:MM`, local timezone) at the right end of the 5h / Week bars**
- **Shows `repo/branch` to the right of the model name** when inside a Git repository
- **Shows accumulated `$X.XX` cost only when using the API** (hidden for Claude.ai subscription users)
- Falls back to `N/A` when rate-limit info is unavailable (e.g. non-subscribers, fresh sessions)
- Pure standard library — no external dependencies

## Display contents

| Row | Content | Source field |
|----|------|----|
| 1 | Model name (bold) + `repo/branch` + `$cost` (API only) | `model.display_name` / `workspace.project_dir` + `git rev-parse` / `cost.total_cost_usd` |
| 2 | Context bar + % | `context_window.used_percentage` |
| 3 | 5h bar + % + ↻ reset time | `rate_limits.five_hour.used_percentage` / `.resets_at` |
| 4 | Week bar + % + ↻ reset time | `rate_limits.seven_day.used_percentage` / `.resets_at` |

The 5h / Week values are passed in directly by Claude Code, so they reflect the **actual subscription remaining**. Missing values fall back to `N/A`.

`resets_at` is provided as a Unix epoch seconds integer, so this script converts it to **the local timezone** for display. The 5h reset always falls within the current day, so it is shown as `HH:MM`; the weekly reset can be several days out, so it is shown as `M/D HH:MM`. If only `resets_at` is missing while `used_percentage` is present, the timestamp is omitted and only the percentage is shown.

The repository name is the basename of `workspace.project_dir`; the branch name comes from `git rev-parse --abbrev-ref HEAD` (falling back to a short SHA when in detached HEAD state). Outside a Git repository, only the directory name is shown.

The cost is shown only when **API-key usage is certain** (i.e. when the subscription check below fails). The subscription check is two-step:

1. If the current JSON contains `rate_limits`, treat as subscription immediately.
2. If `rate_limits` was ever seen previously in the same `session_id`, treat as subscription (recorded as an empty file at `~/.cache/claude-code-statusline/<session_id>.subscription`).

This two-step check prevents cost from leaking to subscription users on frames where `rate_limits` is briefly missing (e.g. right after `/compact`). The marker is a 0-byte empty file; you can delete `~/.cache/claude-code-statusline/` anytime when it is no longer needed.

## Requirements

- Claude Code
- Python 3.8+
- A 256-color capable terminal with a monospace font that renders Unicode block characters cleanly (modern terminals like Windows Terminal, VS Code's integrated terminal, Alacritty, iTerm2 all work)

## Installation

### 1. Place the script

**Option A: Grab the single file (fastest, recommended)**

```bash
curl -L https://raw.githubusercontent.com/YATA-NODE/claude-code-statusline/main/statusline.py -o ~/.claude/statusline.py
```

**Option B: Clone, then copy**

```bash
git clone https://github.com/YATA-NODE/claude-code-statusline.git
cp claude-code-statusline/statusline.py ~/.claude/statusline.py
```

### 2. Add `statusLine` to `~/.claude/settings.json`

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 /home/<your-user>/.claude/statusline.py",
    "padding": 0,
    "refreshInterval": 60000
  }
}
```

Replace `/home/<your-user>/` with your actual home directory absolute path. `~` is **not** expanded here.

### 3. Restart Claude Code

```bash
/exit
claude --continue
```

## Customization

Key constants live near the top of `statusline.py`:

| Constant | Default | Purpose |
|------|----------|------|
| `BAR_WIDTH` | `24` | Bar width in cells |
| `LABEL_WIDTH` | `9` | Minimum width of the left-side label column |
| `FILL_CHAR` | `▆` | Filled cell (lower three quarters block) |
| `EMPTY_CHAR` | `▆` | Empty cell (same shape, only color differs) |
| `EMPTY_COLOR` | `\033[38;5;238m` | Color for empty cells (xterm-256 dark gray) |

### Change stage-color thresholds

Edit `60` / `80` inside `color_for()`:

```python
def color_for(pct: int) -> str:
    if pct < 0:    return "\033[90m"
    if pct < 60:   return "\033[32m"   # green upper bound
    if pct < 80:   return "\033[33m"   # yellow upper bound
    return "\033[31m"
```

### Change the `/compact` warning threshold

Edit `80` inside `main()`:

```python
if label == "Context" and pct >= 80:
    line += f"  \033[1;31m⚠ /compact 推奨\033[0m"
```

### Fallback for terminals without 256-color support

Switch `EMPTY_COLOR` to a 16-color value:

```python
EMPTY_COLOR = "\033[90m"   # bright black (16 colors)
```

## How it works

Claude Code periodically runs the command in `statusLine.command` and renders its stdout right below the input prompt. The current session info is provided to stdin as JSON (`model`, `context_window`, `rate_limits`, `cost`, `workspace`, `transcript_path`, etc.). This script reads `model` / `workspace` / `cost` / `context_window` / `rate_limits`, and additionally invokes `git rev-parse` once to resolve the branch name when needed.

## License

MIT License — see [LICENSE](LICENSE) for details.
