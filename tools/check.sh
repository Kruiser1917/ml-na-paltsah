#!/bin/zsh
set -euo pipefail
DIR="${0:A:h}"
ROOT="${DIR:h}"
CH="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
W=${1:-1440}
H=${2:-900}
mkdir -p /tmp/mlnp_test
python3 -I "$DIR/build_test.py" "$ROOT/index.html" /tmp/mlnp_test/index.html
"$CH" --headless=new --disable-gpu --window-size=$W,$H --virtual-time-budget=8000 --dump-dom "file:///tmp/mlnp_test/index.html?check=1" 2>/dev/null | grep -o 'data-check="[^"]*"' | sed 's/&quot;/"/g' | head -c 4000
echo
