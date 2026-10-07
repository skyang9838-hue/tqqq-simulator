# -*- coding: utf-8 -*-
"""
연도별로 집계해 노이즈를 걷어낸 뒤 조달비용·변동성 계수를 추정한다.

각 (상품, 연도) 에 대해
   y = 실제평균일수익 - [L*r_ndx + div - ER/252]      (= -조달비용 - 마찰)
   x1 = (L-1) * 평균 rate_daily
   x2 = (L-1) * 평균 |r_ndx|
회귀:  y = a - b*x1 - c*x2
  b : 조달금리 계수 (1이면 T-bill 그대로)
  c : 리밸런싱/변동성 비용 계수
  a : 잔여 상수
"""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS
from model import ndx_div_series, daily_returns

ER = {"qqq": 0.0020, "qld": 0.0095, "tqqq": 0.0084}
LEV = {"qqq": 1, "qld": 2, "tqqq": 3}

ndx = load_series("ndx", "close")
irx = load_series("irx", "close")
r_ndx = daily_returns(ndx)
irx_ff = forward_fill(irx, sorted(set(irx) | set(ndx)))
rate = {d: irx_to_daily_rate(irx_ff[d]) for d in sorted(ndx) if d in irx_ff}
div = ndx_div_series(sorted(ndx))

rows = []   # (sym, year, y, x1, x2, n)
for sym in ("qqq", "qld", "tqqq"):
    L, er = LEV[sym], ER[sym]
    lev = load_series(sym, "adjclose"); r = daily_returns(lev)
    ds = [d for d in sorted(r) if d in r_ndx and d in rate]
    yb = {}
    for d in ds:
        yb.setdefault(d[:4], []).append(d)
    for y, dd in sorted(yb.items()):
        if len(dd) < 100:      # 부분연도 제외
            continue
        ya = float(np.mean([r[d] - (L * r_ndx[d] + div[d] - er / TRADING_DAYS) for d in dd]))
        x1 = float(np.mean([(L - 1) * rate[d] for d in dd]))
        x2 = float(np.mean([(L - 1) * abs(r_ndx[d]) for d in dd]))
        rows.append((sym, y, ya, x1, x2, len(dd)))

print("=" * 100)
print("연도별 집계 (연율 %)")
print("=" * 100)
print(f"  {'상품':5s} {'연도':5s} {'잔차y':>9s} {'(L-1)*금리':>11s} {'(L-1)*|r|':>11s} {'일수':>5s}")
for s, y, ya, x1, x2, n in rows:
    print(f"  {s.upper():5s} {y:5s} {ya*TRADING_DAYS*100:+8.3f}% {x1*TRADING_DAYS*100:10.3f}% "
          f"{x2*TRADING_DAYS*100:10.2f}% {n:5d}")

Y  = np.array([r[2] for r in rows])
X1 = np.array([r[3] for r in rows])
X2 = np.array([r[4] for r in rows])
W  = np.array([r[5] for r in rows], dtype=float)
w  = np.sqrt(W / W.mean())

def fit(cols, names, use_w=True):
    X = np.column_stack(cols)
    if use_w:
        coef, *_ = np.linalg.lstsq(X * w[:, None], Y * w, rcond=None)
    else:
        coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    pred = X @ coef
    resid = Y - pred
    ss = 1 - float(np.sum((resid*w)**2)) / float(np.sum(((Y-np.average(Y,weights=W))*w)**2))
    print("\n  " + " | ".join(f"{n}={c:+.5f}" for n, c in zip(names, coef)) + f"   R2={ss:.4f}")
    print(f"    가중 RMSE(연율) = {np.sqrt(np.average(resid**2, weights=W))*TRADING_DAYS*100:.3f}%p")
    return coef, resid

print("\n" + "=" * 100)
print("회귀")
print("=" * 100)
print("\n[A] y = -b*x1                      (조달금리 계수만)")
cA, rA = fit([-X1], ["b"])
print("\n[B] y = a - b*x1                   (+ 상수)")
cB, rB = fit([np.ones(len(Y)), -X1], ["a", "b"])
print("\n[C] y = a - b*x1 - c*x2            (+ 변동성)")
cC, rC = fit([np.ones(len(Y)), -X1, -X2], ["a", "b", "c"])

print("\n" + "=" * 100)
print("모델 C 의 연도별 잔차 (연율)")
print("=" * 100)
for i, (s, y, ya, x1, x2, n) in enumerate(rows):
    print(f"  {s.upper():5s} {y}  {rC[i]*TRADING_DAYS*100:+7.3f}%p")
a, b, c = cC
print(f"\n  해석: 실효 조달금리 = T-bill(BEY) x {b:.4f}")
print(f"        변동성 비용   = (L-1) x |일간수익률| x {c:.4f}")
print(f"        잔여 상수     = {a*TRADING_DAYS*100:+.4f}%/년")
np.save("data/coef_annual.npy", np.array([a, b, c]))
print("\n  -> data/coef_annual.npy 저장")
