#!/usr/bin/env python3
"""Multi-viewport layout, typography, collision, and overflow checker.

Usage:
  ./tools/check_layout.py [path/to/index.html] [--mods ML,DL]
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

HOOK = r"""
(async function(){
  const q = new URLSearchParams(location.search);
  if (!q.has('audit')) return;
  if (document.fonts && document.fonts.ready) { try { await document.fonts.ready; } catch(e){} }
  await new Promise(r => setTimeout(r, 250));
  resize(); fitStage(); resize();

  const origBox = D.box.bind(D), origText = D.text.bind(D);
  let curBoxes = [], curTexts = [];

  D.box = function(o){
    origBox(o);
    const a = o.alpha ?? 1, w = o.w ?? .9, h = o.h ?? .9;
    if (a < .25 || w < .01 || h < .01) return;
    const x = o.x ?? 0, y = o.y ?? 0, z = o.z ?? 0;
    const pTL = P(x - w/2, y + h/2, z), pBR = P(x + w/2, y - h/2, z);
    const cssL = pTL[0] / DPR, cssT = pTL[1] / DPR, cssR = pBR[0] / DPR, cssB = pBR[1] / DPR;
    const cssW = Math.abs(cssR - cssL), cssH = Math.abs(cssB - cssT);
    let labelInfo = null;
    if (o.label){
      const ar = w / h, maxW = 80 * ar;
      let fs0 = o.labelSize ?? 44, fs = fs0;
      ctx.save();
      ctx.font = `600 ${fs}px ${MONO}`;
      const mw = ctx.measureText(o.label).width;
      if (mw > maxW) fs = fs * maxW / mw;
      ctx.restore();
      const effCssPx = cssH * (fs / 100);
      labelInfo = { text: o.label, fs0, fs: +fs.toFixed(1), effCssPx: +effCssPx.toFixed(1), shrunk: +(fs / fs0).toFixed(2) };
    }
    curBoxes.push({ l:cssL, t:cssT, r:cssR, b:cssB, w:cssW, h:cssH, x, y, ww:w, wh:h, labelInfo, layer:o.layer ?? 1 });
  };

  D.text = function(o){
    origText(o);
    const a = o.alpha ?? 1;
    if (a < .25 || !o.text) return;
    const p = P(o.x, o.y, o.z ?? 0);
    const fs = (o.size ?? 14) * DPR * TS;
    ctx.save();
    ctx.font = `${o.weight ?? 600} ${fs}px ${o.mono ? MONO : SANS}`;
    const tw = ctx.measureText(o.text).width;
    ctx.restore();
    const cssFs = (o.size ?? 14) * TS;
    let cx = p[0], cy = p[1], clamped = 0;
    if (!o.rot && !o.align){
      const half = tw / 2 + fs * .55 + 6 * DPR;
      const cl = W > half * 2 ? clamp(p[0], half, W - half) : W / 2;
      clamped = Math.abs(cl - p[0]) / DPR;
      cx = cl;
    }
    const cssW = (o.bg ? tw + fs * 1.1 : tw) / DPR;
    const cssH = (o.bg ? fs * 1.75 : fs * 1.2) / DPR;
    let cssL = cx / DPR - cssW / 2, cssR = cx / DPR + cssW / 2;
    if (o.align === 'left'){ cssL = cx / DPR; cssR = cssL + cssW; }
    if (o.align === 'right'){ cssR = cx / DPR; cssL = cssR - cssW; }
    let cssT = cy / DPR - cssH / 2, cssB = cy / DPR + cssH / 2;
    if (o.rot){
      const rw = cssH, rh = cssW;
      cssL = cx / DPR - rw / 2; cssR = cx / DPR + rw / 2;
      cssT = cy / DPR - rh / 2; cssB = cy / DPR + rh / 2;
    }
    curTexts.push({ text:o.text, size:o.size ?? 14, cssFs:+cssFs.toFixed(1), l:+cssL.toFixed(1), t:+cssT.toFixed(1), r:+cssR.toFixed(1), b:+cssB.toFixed(1), w:+cssW.toFixed(1), h:+cssH.toFixed(1), clamped:+clamped.toFixed(1), bg:!!o.bg, rot:!!o.rot, wx:o.x, wy:o.y });
  };

  const targetMods = (q.get('mods') || 'ML,DL').split(',');
  const report = [];

  for (let mi = 0; mi < MODULES.length; mi++){
    const M = MODULES[mi];
    if (!targetMods.includes(M.name)) continue;
    for (let li = 0; li < M.lessons.length; li++){
      const L = M.lessons[li];
      openLesson(li, false, mi);
      fitStage(); resize();
      const stgR = stage.getBoundingClientRect();
      const icR = document.querySelector('.intro-card').getBoundingClientRect();
      const stripH = document.getElementById('strip').getBoundingClientRect().height;
      const scMaxH = Math.max(...Array.from(document.querySelectorAll('#strip .sc')).map(el => el.getBoundingClientRect().height));

      begin();
      idx = L.scenes.length - 1; phase = 'done'; ovKey = '';
      overlays(L.scenes[idx], -1);
      const endDiv = document.querySelector('#end > div');
      const endH = endDiv ? endDiv.getBoundingClientRect().height : 0;

      const lIssues = [];
      if (icR.height > stgR.height - 12) lIssues.push(`INTRO_OVERFLOW: ${Math.round(icR.height)}px > stage ${Math.round(stgR.height)}px`);
      if (endH > stgR.height - 12) lIssues.push(`END_OVERFLOW: ${Math.round(endH)}px > stage ${Math.round(stgR.height)}px`);
      // 1 line .sc = 55px, 2 lines = 70px, 3 lines = 86px -> flag >= 3 lines
      if (scMaxH > 76) lIssues.push(`STRIP_TALL: max .sc height ${Math.round(scMaxH)}px (strip total ${Math.round(stripH)}px)`);

      const sceneReports = [];
      for (let si = 0; si < L.scenes.length; si++){
        const S = L.scenes[si];
        load(si, false);
        phase = 'play';
        const notesEl = document.querySelector('.notes');
        const maxNotesH = S.beats.length > 3 ? 960 : 900;
        const sIssues = [];
        if (notesEl.scrollHeight > maxNotesH) sIssues.push(`NOTES_BLOATED: scrollH=${notesEl.scrollHeight}px > ${maxNotesH}px`);

        const sampleTimes = S.beats.map((b, bi) => ({ tag:`beat${bi}`, k:bi, tt: Math.min(S.dur - .05, (bi + 1 < S.beats.length ? (b.t + S.beats[bi+1].t)/2 : (b.t + S.dur)/2)) }));
        sampleTimes.push({ tag:'poster', k:S.beats.length - 1, tt:S.poster });

        for (const st of sampleTimes){
          t = st.tt; ovKey = ''; lastHud = null;
          overlays(S, st.k);
          showHud(S.hud(st.tt));
          curBoxes = []; curTexts = [];
          paint(S, st.tt);

          const codeEl = document.getElementById('code');
          if (!codeEl.hidden && st.tag !== 'poster'){
            if (codeEl.scrollWidth > codeEl.clientWidth + 2){
              sIssues.push(`${st.tag} CODE_TRUNC: "${codeEl.textContent}" (${codeEl.scrollWidth} > ${codeEl.clientWidth})`);
            }
            if ((S.beats[st.k].code || '').includes('\n')){
              sIssues.push(`${st.tag} CODE_NEWLINE: "${S.beats[st.k].code.replace(/\n/g, ' \\n ')}"`);
            }
          }
          const capEl = document.getElementById('caption');
          const capR = !capEl.hidden ? capEl.getBoundingClientRect() : null;
          if (capR && st.tag !== 'poster' && capR.height > 104){
            sIssues.push(`${st.tag} CAPTION_TALL: ${Math.round(capR.height)}px (${S.beats[st.k].text.length} chars)`);
          }
          const ovR = document.querySelector('.ov').getBoundingClientRect();
          const capTopRel = capR ? capR.top - stgR.top : stgR.height;
          const ovBotRel = ovR.bottom - stgR.top;

          for (const bx of curBoxes){
            if (bx.labelInfo){
              if (bx.labelInfo.effCssPx < 11.2){
                sIssues.push(`${st.tag} TINY_BOX_LABEL: "${bx.labelInfo.text}" effPx=${bx.labelInfo.effCssPx}px (labelSize=${bx.labelInfo.fs0}, shrunk=${bx.labelInfo.shrunk}, boxH=${Math.round(bx.h)}px)`);
              } else if (bx.labelInfo.shrunk < 0.72){
                sIssues.push(`${st.tag} SHRUNK_BOX_LABEL: "${bx.labelInfo.text}" shrunk=${bx.labelInfo.shrunk} effPx=${bx.labelInfo.effCssPx}px`);
              }
            }
            if (!bx.labelInfo && bx.w > 64 && bx.h > 46){
              for (const tx of curTexts){
                if (!tx.rot && !tx.bg && Math.abs((tx.l + tx.r)/2 - (bx.l + bx.r)/2) < 10 && tx.t > bx.t + 2 && tx.b < bx.b - 2){
                  if (tx.w > bx.w - 6){
                    sIssues.push(`${st.tag} TEXT_OVERFLOWS_CARD: "${tx.text}" textW=${Math.round(tx.w)}px > cardW=${Math.round(bx.w)}px`);
                  }
                }
              }
            }
          }

          for (let i = 0; i < curTexts.length; i++){
            const tx = curTexts[i];
            const isTick = /^-?\d+([.,]\d+)?%?$/.test(tx.text.trim());
            if (!isTick && tx.size < 10.5){
              sIssues.push(`${st.tag} SMALL_TEXT: "${tx.text}" size=${tx.size} (css=${tx.cssFs}px)`);
            }
            if (tx.clamped > 3){
              sIssues.push(`${st.tag} EDGE_CLAMPED: "${tx.text}" clamped=${tx.clamped}px`);
            }
            if (capR && tx.b > capTopRel + 2){
              sIssues.push(`${st.tag} HITS_CAPTION: "${tx.text}" bottom=${Math.round(tx.b)} > capTop=${Math.round(capTopRel)}`);
            }
            if (tx.t < ovBotRel - 2 && tx.l < (ovR.right - stgR.left)){
              sIssues.push(`${st.tag} HITS_HUD: "${tx.text}" top=${Math.round(tx.t)} < hudBot=${Math.round(ovBotRel)}`);
            }
            for (let j = i + 1; j < curTexts.length; j++){
              const ty = curTexts[j];
              if (tx.rot !== ty.rot) continue;
              const ox = Math.min(tx.r, ty.r) - Math.max(tx.l, ty.l);
              const oy = Math.min(tx.b, ty.b) - Math.max(tx.t, ty.t);
              if (ox > 6 && oy > 4){
                sIssues.push(`${st.tag} TEXT_OVERLAP: "${tx.text}" <-> "${ty.text}" (${Math.round(ox)}x${Math.round(oy)}px)`);
              }
            }
          }
        }
        const uniq = [...new Set(sIssues)];
        if (uniq.length) sceneReports.push({ si, title:S.title, issues:uniq });
      }
      report.push({ mod:M.name, li, short:L.short, lIssues, sceneReports });
    }
  }
  const jsonStr = JSON.stringify(report);
  document.body.setAttribute('data-audit', jsonStr);
  if (window.parent && window.parent !== window) window.parent.postMessage({ mlAudit: jsonStr }, '*');
})();
"""


def main() -> int:
    default_html = pathlib.Path(__file__).resolve().parent.parent / "index.html"
    ap = argparse.ArgumentParser(description="Check layout & typography across Desktop, Laptop, and Mobile viewports.")
    ap.add_argument("html", nargs="?", default=str(default_html), help="Path to index.html")
    ap.add_argument("--mods", default="ML,DL", help="Comma-separated module names to check (default: ML,DL)")
    args = ap.parse_args()

    src_path = pathlib.Path(args.html).expanduser().resolve()
    src = src_path.read_text(encoding="utf-8")
    idx = src.rfind("})();")
    if idx < 0:
        print("ERROR: Could not find closing '})();' in HTML script", file=sys.stderr)
        return 2

    tmp_dir = pathlib.Path("/tmp/mlnp_test")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    audit_html = tmp_dir / "audit_layout.html"
    audit_html.write_text(src[:idx] + HOOK + src[idx:], encoding="utf-8")

    chrome = os.environ.get("CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    viewports = [
        (1440, 900, "Desktop 1440x900"),
        (1280, 800, "Laptop 1280x800"),
        (390, 844, "Mobile 390x844"),
    ]

    total_issues = 0
    phone_wrapper = tmp_dir / "audit_phone.html"
    try:
        for w, h, label in viewports:
            if w < 500:
                phone_wrapper.write_text(
                    f"<!doctype html><html><body style='margin:0'>"
                    f"<script>window.addEventListener('message', e => {{"
                    f"  if (e.data && e.data.mlAudit) document.body.setAttribute('data-audit', e.data.mlAudit);"
                    f"}});</script>"
                    f"<iframe src='audit_layout.html?audit=1&mods={args.mods}' "
                    f"style='width:{w}px;height:{h}px;border:0;display:block'></iframe>"
                    f"</body></html>",
                    encoding="utf-8",
                )
                target_url = f"file://{phone_wrapper}"
                win_w, win_h = 520, h + 20
            else:
                target_url = f"file://{audit_html}?audit=1&mods={args.mods}"
                win_w, win_h = w, h

            cmd = [
                chrome,
                "--headless=new",
                "--disable-gpu",
                f"--window-size={win_w},{win_h}",
                "--virtual-time-budget=14000",
                "--dump-dom",
                target_url,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            m = re.search(r'data-audit="([^"]*)"', res.stdout)
            if not m:
                print(f"=== {label}: ERROR (no data-audit output) ===")
                total_issues += 1
                continue
            data = json.loads(
                m.group(1)
                .replace("&quot;", '"')
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
            )
            vp_issues = 0
            print(f"=== {label} ===")
            for item in data:
                s_cnt = sum(len(sr["issues"]) for sr in item["sceneReports"])
                l_cnt = len(item["lIssues"])
                if l_cnt or s_cnt:
                    vp_issues += l_cnt + s_cnt
                    print(f"  [{item['mod']} #{item['li']} {item['short']}] lesson_issues={item['lIssues']}")
                    for sr in item["sceneReports"]:
                        print(f"    Scene {sr['si'] + 1} ({sr['title']}):")
                        for iss in sr["issues"]:
                            print(f"      - {iss}")
            if vp_issues == 0:
                print(f"  OK: 0 layout/typography issues across {len(data)} lessons")
            total_issues += vp_issues
    finally:
        audit_html.unlink(missing_ok=True)
        phone_wrapper.unlink(missing_ok=True)

    return 1 if total_issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
