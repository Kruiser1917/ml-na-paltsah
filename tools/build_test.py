#!/usr/bin/env python3
"""Inject headless check (?check=1) and screenshot (?shot=m,l,s,t) harness."""
import pathlib
import sys

src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
snippet = r"""
(function(){
  const q = new URLSearchParams(location.search);
  if (q.has('check')){
    const errs = []; let n = 0;
    MODULES.forEach((M) => M.lessons.forEach((L, li) => L.scenes.forEach((S, si) => {
      for (let k = 0; k <= 60; k++){ const tt = S.dur * k / 60;
        try { LIST.length = 0; setCam(S.frame(tt)); S.draw(tt, D); S.hud(tt); for (const it of LIST) it.draw(); n++; }
        catch (e) { errs.push(M.name + '/' + li + '/' + si + ' t=' + tt.toFixed(2) + ': ' + e.message); break; } }
      S.beats.forEach((b, i) => { if (!b.say) errs.push(M.name + '/' + li + '/' + si + ' beat ' + i + ' no say'); if (i && b.t <= S.beats[i-1].t) errs.push(M.name + '/' + li + '/' + si + ' beat order'); });
      if (!S.key || !S.keySay || !S.terms || !S.intro) errs.push(M.name + '/' + li + '/' + si + ' meta missing');
    })));
    document.body.setAttribute('data-check', JSON.stringify({ n, errs }));
  }
  if (q.has('shot')){ const [m, l, s, tt] = q.get('shot').split(',').map(Number); openLesson(l, false, m); begin(); load(s, false); t = tt; }
})();
"""
i = src.rfind("})();")
out = src[:i] + snippet + src[i:]
out_path = pathlib.Path(sys.argv[2])
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(out, encoding="utf-8")
