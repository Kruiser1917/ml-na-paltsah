#!/bin/zsh
# Usage: tools/shot.sh out.png "m,l,s,t" [width height]   (width < 500 -> phone via iframe)
set -euo pipefail
DIR="${0:A:h}"
ROOT="${DIR:h}"
CH="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
W=${3:-1440}
H=${4:-900}
mkdir -p /tmp/mlnp_test
python3 -I "$DIR/build_test.py" "$ROOT/index.html" /tmp/mlnp_test/index.html
if (( W < 500 )); then
  print "<html><body style='margin:0;background:#fff'><iframe src='index.html?shot=$2' style='width:${W}px;height:${H}px;border:0;display:block'></iframe></body></html>" > /tmp/mlnp_test/phone.html
  "$CH" --headless=new --disable-gpu --hide-scrollbars --window-size=520,$H --virtual-time-budget=3000 --screenshot="$1" "file:///tmp/mlnp_test/phone.html" >/dev/null 2>&1
else
  "$CH" --headless=new --disable-gpu --hide-scrollbars --window-size=$W,$H --virtual-time-budget=2500 --screenshot="$1" "file:///tmp/mlnp_test/index.html?shot=$2" >/dev/null 2>&1
fi
