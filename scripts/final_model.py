# -*- coding: utf-8 -*-
"""
확정 모델과 검증.

  r_lev(t) = L*r_ndx(t) + div(t) - (L-1)*max(0, rate(t)-spread) - ER/252

  rate   : ^IRX(13주 T-bill) 할인율 -> 채권등가수익률 -> 일할
  spread : 13주 T-bill 과 실제 오버나이트 조달금리의 차. QQQ/QLD/TQQQ
           동일기간 잔차가 (L-1) 에 정확히 비례하는 것에서 실측했다.
  div    : NDX 일간 배당수익률 (QQQ 실지급 배당 기반, 2004.7~ 실측)
"""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS
from model import ndx_div_series, daily_returns

SPREAD_ANNUAL = 0.00374          # 실측 (아래 solve_spread 로 재확인)
ER = {"qqq": 0.0020, "qld": 0.0095, "tqqq": 0.0084}
LEV = {"qqq": 1, "qld": 2, "tqqq": 3}


class Model:
    def __init__(self, spread=SPREAD_ANNUAL, pre2004_div=0.005):
        self.spread = spread
        ndx = load_series("ndx", "close")
        irx = load_series("irx", "close")
        self.dates = sorted(ndx)
        self.r_ndx = daily_returns(ndx)
        irx_ff = forward_fill(irx, sorted(set(irx) | set(ndx)))
        self.rate = {d: irx_to_daily_rate(irx_ff[d]) for d in self.dates if d in irx_ff}
        self.div = ndx_div_series(self.dates, pre2004=pre2004_div)

    def daily(self, d, L, er):
        """하루치 모델 수익률. 데이터 없으면 None."""
        if d not in self.r_ndx or d not in self.rate:
            return None
        eff = max(0.0, self.rate[d] - self.spread / TRADING_DAYS)
        return L * self.r_ndx[d] + self.div[d] - (L - 1) * eff - er / TRADING_DAYS


def ann(g, n): return g ** (TRADING_DAYS / n) - 1.0 if n > 0 and g > 0 else float("nan")


def solve_spread():
    """QLD/TQQQ 잔차를 0으로 만드는 spread 를 격자탐색으로 찾는다."""
    best = None
    for s in np.arange(0.0, 0.010, 0.0001):
        m = Model(spread=float(s))
        errs = []
        for sym in ("qld", "tqqq"):
            L, er = LEV[sym], ER[sym]
            lev = load_series(sym, "adjclose"); r = daily_returns(lev)
            ds = [d for d in sorted(r) if d >= "2010-02-12" and m.daily(d, L, er) is not None]
            ga = gm = 1.0
            for d in ds:
                ga *= 1 + r[d]; gm *= 1 + m.daily(d, L, er)
            errs.append(ann(ga, len(ds)) - ann(gm, len(ds)))
        score = sum(e * e for e in errs)
        if best is None or score < best[0]:
            best = (score, float(s), errs)
    return best


def verify(spread):
    m = Model(spread=spread)
    print(f"\n{'='*92}")
    print(f"검증: spread = {spread*100:.3f}%/년")
    print(f"{'='*92}")
    print(f"  {'상품':6s} {'L':>2s}  {'기간':24s} {'실제':>9s} {'모델':>9s} {'차이':>8s}  {'최종배수 실제/모델':>22s}")
    out = {}
    for sym in ("qqq", "qld", "tqqq"):
        L, er = LEV[sym], ER[sym]
        lev = load_series(sym, "adjclose"); r = daily_returns(lev)
        ds = [d for d in sorted(r) if m.daily(d, L, er) is not None]
        ga = gm = 1.0
        yb = {}
        for d in ds:
            ra, rm = r[d], m.daily(d, L, er)
            ga *= 1 + ra; gm *= 1 + rm
            yb.setdefault(d[:4], []).append(ra - rm)
        n = len(ds)
        a, b = ann(ga, n), ann(gm, n)
        print(f"  {sym.upper():6s} {L:2d}  {ds[0]}~{ds[-1]} {a*100:8.3f}% {b*100:8.3f}% "
              f"{(a-b)*100:+7.3f}%p  {ga:10.2f} / {gm:<10.2f}")
        out[sym] = (yb, ds)
    return m, out


def year_table(out):
    print(f"\n{'='*92}")
    print("연도별 모델 오차 (실제 - 모델, 연율)  +면 모델이 낮게 잡음 = 보수적")
    print(f"{'='*92}")
    years = sorted({y for yb, _ in out.values() for y in yb})
    print(f"  {'연도':6s} {'QQQ':>9s} {'QLD':>9s} {'TQQQ':>9s}")
    for y in years:
        row = f"  {y:6s}"
        for sym in ("qqq", "qld", "tqqq"):
            yb, _ = out[sym]
            if y in yb:
                v = float(np.mean(yb[y])) * TRADING_DAYS * 100
                row += f" {v:+8.2f}%"
            else:
                row += f" {'-':>9s}"
        print(row)
    print()
    for sym in ("qqq", "qld", "tqqq"):
        yb, _ = out[sym]
        vals = [float(np.mean(v)) * TRADING_DAYS for v in yb.values()]
        print(f"  {sym.upper():5s} 연도별오차: 평균 {np.mean(vals)*100:+.3f}%p  "
              f"표준편차 {np.std(vals)*100:.3f}%p  "
              f"최악 {min(vals)*100:+.2f}%p  최고 {max(vals)*100:+.2f}%p")


if __name__ == "__main__":
    print("spread 격자탐색 중...")
    score, s, errs = solve_spread()
    print(f"  최적 spread = {s*100:.4f}%/년   잔차: QLD {errs[0]*100:+.4f}%p, TQQQ {errs[1]*100:+.4f}%p")
    m, out = verify(s)
    year_table(out)
    with open("data/spread.txt", "w", encoding="utf-8") as f:
        f.write(f"{s:.6f}\n")
    print(f"\n  -> data/spread.txt 에 {s:.6f} 저장")
