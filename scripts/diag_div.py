# -*- coding: utf-8 -*-
"""배당 역산이 깨진 원인 진단."""
import numpy as np
from common import load_series, TRADING_DAYS
import csv, os
from common import RAW

ndx  = load_series("ndx", "close")
qqq_a = load_series("qqq", "adjclose")
qqq_c = load_series("qqq", "close")

# 1) QQQ 실제 배당 내역
divs = []
with open(os.path.join(RAW, "qqq_div.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        divs.append((r["date"], float(r["amount"])))
print("=" * 78)
print("1) QQQ 실제 배당 지급 내역")
print("=" * 78)
print(f"  총 {len(divs)}건  {divs[0][0]} ~ {divs[-1][0]}")
print("  처음 8건:", ", ".join(f"{d}:{a:.4f}" for d, a in divs[:8]))
print("  최근 8건:", ", ".join(f"{d}:{a:.4f}" for d, a in divs[-8:]))

# 연도별 배당합 / 연말 주가 = 배당수익률
byyear = {}
for d, a in divs:
    byyear.setdefault(d[:4], 0.0)
    byyear[d[:4]] += a
print("\n  연도별 배당수익률 (연간배당합 / 그해 마지막 종가):")
years = sorted(byyear)
for y in years:
    ydates = [d for d in qqq_c if d[:4] == y]
    if not ydates:
        continue
    px = qqq_c[max(ydates)]
    print(f"    {y}  배당합 {byyear[y]:7.4f}  종가 {px:8.2f}  ->  {byyear[y]/px*100:5.3f}%")

# 2) NDX vs QQQ 정합성: 가격수익률 차이 분포
print("\n" + "=" * 78)
print("2) NDX 가격수익 vs QQQ 가격수익 (같아야 정상, 배당·보수 무관)")
print("=" * 78)
common = sorted(set(ndx) & set(qqq_c))
prev_n = prev_q = None
diffs = []
for d in common:
    n, q = ndx[d], qqq_c[d]
    if prev_n and prev_q:
        rn = n / prev_n - 1.0
        rq = q / prev_q - 1.0
        diffs.append((d, rq - rn))
    prev_n, prev_q = n, q
arr = np.array([x[1] for x in diffs])
print(f"  표본 {len(arr)}일")
print(f"  평균 {arr.mean()*1e4:+.3f} bp/일  중앙값 {np.median(arr)*1e4:+.3f} bp/일  표준편차 {arr.std()*1e4:.1f} bp")
worst = sorted(diffs, key=lambda x: abs(x[1]), reverse=True)[:12]
print("  |차이| 최대 12일:")
for d, v in worst:
    print(f"    {d}  {v*100:+8.3f}%")

# 연도별 평균 차이
print("\n  연도별 평균 차이 (bp/일 -> 연율):")
yb = {}
for d, v in diffs:
    yb.setdefault(d[:4], []).append(v)
for y in sorted(yb):
    m = float(np.mean(yb[y]))
    md = float(np.median(yb[y]))
    print(f"    {y}  평균 {m*1e4:+7.3f}bp (연 {m*TRADING_DAYS*100:+6.2f}%)   중앙값 {md*1e4:+7.3f}bp")
