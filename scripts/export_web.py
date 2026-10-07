# -*- coding: utf-8 -*-
"""시뮬레이터 HTML 에 임베드할 JSON 데이터를 만든다."""
import csv, json

rows = []
with open("data/series.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

dates = [r["date"] for r in rows]
# 값은 유효숫자 7자리면 충분 (지수 레벨)
tqqq = [float(f"{float(r['tqqq']):.7g}") for r in rows]
qqq  = [float(f"{float(r['qqq']):.7g}")  for r in rows]
ndx  = [float(f"{float(r['ndx']):.7g}")  for r in rows]

# 월 첫 거래일 인덱스
month_first, months = {}, []
for i, d in enumerate(dates):
    ym = d[:7]
    if ym not in month_first:
        month_first[ym] = i
        months.append(ym)

# 실제/모델 경계
tq_real = next((i for i, r in enumerate(rows) if r["tqqq_src"] == "real"), None)
qq_real = next((i for i, r in enumerate(rows) if r["qqq_src"] == "real"), None)

payload = {
    "start": dates[0],
    "end": dates[-1],
    "n": len(dates),
    "dates": dates,
    "tqqq": tqqq,
    "qqq": qqq,
    "ndx": ndx,
    "months": months,
    "monthIdx": [month_first[m] for m in months],
    "realFrom": {"tqqq": tq_real, "qqq": qq_real},
}
js = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
with open("data/web_data.json", "w", encoding="utf-8") as f:
    f.write(js)
print(f"rows={len(dates)}  months={len(months)}")
print(f"tqqq real from index {tq_real} ({dates[tq_real]}), qqq from {qq_real} ({dates[qq_real]})")
print(f"json size = {len(js.encode('utf-8'))/1024:.1f} KB")
