# -*- coding: utf-8 -*-
"""上线前措辞自检：dist 里任何页面命中禁用词就退出码 1（每日刷新与手动补部署共用）。"""
import glob, io, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from core.wording import lint
bad = 0
for f in glob.glob(os.path.join(ROOT, 'site/dist/*.html')) + glob.glob(os.path.join(ROOT, 'site/dist/s/*.html')):
    hits = [x for x in lint(io.open(f, encoding='utf-8').read()) if x[1] == 'banned_term']   # 只拦禁用词；第三方模型原名里的“最强”之类最高级不拦
    if hits: bad += 1; print('措辞违规', os.path.relpath(f, ROOT), hits[:2])
print('措辞自检：违规页面', bad); sys.exit(1 if bad else 0)
