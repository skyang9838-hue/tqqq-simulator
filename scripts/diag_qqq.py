# -*- coding: utf-8 -*-
"""QQQ(L=1)로 데이터·배당 계산을 검증하고, 동일기간 비교로 TQQQ 잔차를 재확인한다."""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS
from model import ndx_div_series, daily_returns

ndx = load_series("ndx", "close")
irx = load_series("irx", "close")
r_ndx = daily_returns(ndx)
irx_ff = forward_fill(irx, sorted(set(irx) | set(ndx)))
div = ndx_div_series(sorted(ndx))

def ann(g, n): return g ** (TRADING_DAYS / n) - 1.0 if n > 0 and g > 0 else float("nan")

def run(sym, L, er, start=None, end=None, label=None):
    lev = load_series(sym, "adjclose")
    r_lev = daily_returns(lev)
    ds = [d for d in sorted(r_lev) if d in r_ndx and d in irx_ff]
    if start: ds = [d for d in ds if d >= start]
    if end:   ds = [d for d in ds if d <= end]
    n = len(ds)
    if n < 50: 
        print(f"  {label or sym}: 표본 부족({n})"); return
    g_act = g_mod = 1.0
    for d in ds:
        r, rt, dv = r_ndx[d], irx_to_daily_rate(irx_ff[d]), div[d]
        g_act *= 1 + r_lev[d]
        g_mod *= 1 + L * r - (L - 1) * rt + dv - er / TRADING_DAYS
    gap = ann(g_act, n) - ann(g_mod, n)
    print(f"  {label or sym.upper():22s} {ds[0]}~{ds[-1]} {n:5d}일  "
          f"실제 연{ann(g_act,n)*100:7.3f}%  모델 연{ann(g_mod,n)*100:7.3f}%  차이 {gap*100:+6.3f}%p")
    return gap

print("=" * 96)
print("A) QQQ (L=1) 검증 — 조달비용이 없어 데이터·배당 계산만 시험한다")
print("=" * 96)
run("qqq", 1, 0.0020, label="QQQ 전체(1999~)")
run("qqq", 1, 0.0020, start="2004-07-01", label="QQQ 2004.7~ (배당실측구간)")
run("qqq", 1, 0.0020, start="2010-02-12", label="QQQ 2010.2~ (TQQQ와 동일기간)")

print("\n" + "=" * 96)
print("B) 동일기간(2010-02-12~) 비교")
print("=" * 96)
for sym, L, er in (("qqq",1,0.0020), ("qld",2,0.0095), ("tqqq",3,0.0084)):
    run(sym, L, er, start="2010-02-12", label=f"{sym.upper()} L={L}")

print("\n" + "=" * 96)
print("C) TQQQ 분할/조정 정합성 — close 대비 adjclose 누적 조정계수")
print("=" * 96)
for sym in ("tqqq", "qld", "qqq"):
    c = load_series(sym, "close"); a = load_series(sym, "adjclose")
    ds = sorted(set(c) & set(a))
    f0 = c[ds[0]] / a[ds[0]]; f1 = c[ds[-1]] / a[ds[-1]]
    print(f"  {sym.upper():5s} 시작 {ds[0]} close/adj={f0:9.4f}   끝 {ds[-1]} close/adj={f1:7.4f}"
          f"   누적조정 {f0/f1:9.4f}배")
