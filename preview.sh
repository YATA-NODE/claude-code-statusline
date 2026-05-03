#!/usr/bin/env bash
# preview.sh — README 掲載のスクショと同じ 3 ケースを縦に並べて再現する。
#
# 使い方:  bash preview.sh
# 出力:    上下端と各ケース間に空行を 1 行ずつ挟んで、シェルプロンプトと
#          くっつかないように整える。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SL="$SCRIPT_DIR/statusline.py"

NOW=$(date +%s)
FIVE=$((NOW + 2 * 3600))     # 5h リセットを 2 時間後に設定
WEEK=$((NOW + 4 * 86400))    # 週次リセットを 4 日後に設定

# Case A: サブスクリプション通常運用（5h は 60% で黄色になる帯域）
case_a='{"model":{"display_name":"Opus 4.7 (1M context)"},'
case_a+='"workspace":{"project_dir":"'"$SCRIPT_DIR"'"},'
case_a+='"context_window":{"used_percentage":35},'
case_a+='"rate_limits":{'
case_a+='"five_hour":{"used_percentage":60,"resets_at":'"$FIVE"'},'
case_a+='"seven_day":{"used_percentage":25,"resets_at":'"$WEEK"'}}}'

# Case B: Context 逼迫（92% で /compact 推奨警告が出る）
case_b='{"model":{"display_name":"Opus 4.7 (1M context)"},'
case_b+='"workspace":{"project_dir":"'"$SCRIPT_DIR"'"},'
case_b+='"context_window":{"used_percentage":92},'
case_b+='"rate_limits":{'
case_b+='"five_hour":{"used_percentage":55,"resets_at":'"$FIVE"'},'
case_b+='"seven_day":{"used_percentage":40,"resets_at":'"$WEEK"'}}}'

# Case C: API 利用（rate_limits 不在、cost あり → ドル金額が末尾に表示）
case_c='{"model":{"display_name":"Sonnet 4.6"},'
case_c+='"workspace":{"project_dir":"'"$SCRIPT_DIR"'"},'
case_c+='"context_window":{"used_percentage":12},'
case_c+='"cost":{"total_cost_usd":0.42}}'

echo
for js in "$case_a" "$case_b" "$case_c"; do
  python3 "$SL" <<<"$js"
  echo   # statusline.py は末尾改行を出さないので最終行を確定させる
  echo   # ケース間（および末尾）の空行
done
