# -*- coding: utf-8 -*-
"""template.html + web_data.json + app.js -> 시뮬레이터.html (단일 파일)"""
import json
import os
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

tpl = open(os.path.join(ROOT, "web", "template.html"), encoding="utf-8").read()
app = open(os.path.join(ROOT, "web", "app.js"), encoding="utf-8").read()
data = json.load(open(os.path.join(ROOT, "data", "web_data.json"), encoding="utf-8"))

# 모델 계수를 데이터에 실어 보낸다 (방법론 섹션에서 표시)
coef = {}
cpath = os.path.join(ROOT, "data", "coef.txt")
if os.path.exists(cpath):
    for line in open(cpath, encoding="utf-8"):
        parts = line.strip().split("\t")
        if len(parts) == 2:
            coef[parts[0]] = float(parts[1])
data["coef"] = {"b": coef.get("b", 1.0398), "c": coef.get("c", 0.00151)}
data["built"] = dt.date.today().isoformat()

payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
assert "</script" not in payload.lower(), "데이터에 script 종료 태그가 들어 있다"
assert "__DATA__" in tpl and "__SCRIPT__" in tpl, "템플릿 자리표시자 없음"

out = tpl.replace("__DATA__", payload).replace("__SCRIPT__", app)
path = os.path.join(ROOT, "시뮬레이터.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(out)

# GitHub Pages용: 아티팩트 형식(스켈레톤 없음)에 문서 뼈대를 씌운다
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
            + out + "\n</body>\n</html>\n")

kb = len(out.encode("utf-8")) / 1024
print(f"wrote {path}")
print(f"  size      {kb:,.1f} KB   (한도 16,384 KB)")
print(f"  data      {len(payload)/1024:,.1f} KB")
print(f"  app.js    {len(app)/1024:,.1f} KB")
print(f"  rows      {data['n']:,}   {data['start']} ~ {data['end']}")
print(f"  coef      b={data['coef']['b']:.5f}  c={data['coef']['c']:.6f}")
