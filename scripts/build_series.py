# -*- coding: utf-8 -*-
"""
최종 계수를 확정하고 1985~현재 가상 TQQQ / QQQ 일별 시계열을 만든다.

확정 모델 (a=0 으로 눌러 보수적으로):
  r_lev = L*r_ndx + div - ER/252 - b*(L-1)*rate - c*(L-1)*|r_ndx|

실제 데이터가 있는 구간은 실제 수익률을 쓴다 (하이브리드).
  TQQQ : ~2010-02-10 모델,  2010-02-11~ 실제
  QQQ  : ~1999-03-09 모델,  1999-03-10~ 실제
"""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS
from model import ndx_div_series, daily_returns

ER = {"qqq": 0.0020, "qld": 0.0095, "tqqq": 0.0084}
LEV = {"qqq": 1, "qld": 2, "tqqq": 3}
REAL_START = {"tqqq": "2010-02-11", "qqq": "1999-03-10"}

ndx = load_series("ndx", "close")
irx = load_series("irx", "close")
dates = sorted(ndx)
r_ndx = daily_returns(ndx)
irx_ff = forward_fill(irx, sorted(set(irx) | set(ndx)))
rate = {d: irx_to_daily_rate(irx_ff[d]) for d in dates if d in irx_ff}


def annual_rows(div):
    rows = []
    for sym in ("qqq", "qld", "tqqq"):
        L, er = LEV[sym], ER[sym]
        lev = load_series(sym, "adjclose"); r = daily_returns(lev)
        ds = [d for d in sorted(r) if d in r_ndx and d in rate]
        yb = {}
        for d in ds:
            yb.setdefault(d[:4], []).append(d)
        for y, dd in sorted(yb.items()):
            if len(dd) < 100:
                continue
            ya = float(np.mean([r[d] - (L * r_ndx[d] + div[d] - er / TRADING_DAYS) for d in dd]))
            x1 = float(np.mean([(L - 1) * rate[d] for d in dd]))
            x2 = float(np.mean([(L - 1) * abs(r_ndx[d]) for d in dd]))
            rows.append((sym, y, ya, x1, x2, len(dd)))
    return rows


def fit_bc(rows):
    """a=0 고정, b·c 만 추정 (가중 최소제곱)."""
    Y  = np.array([r[2] for r in rows])
    X1 = np.array([r[3] for r in rows])
    X2 = np.array([r[4] for r in rows])
    W  = np.array([r[5] for r in rows], dtype=float)
    w  = np.sqrt(W / W.mean())
    X = np.column_stack([-X1, -X2])
    coef, *_ = np.linalg.lstsq(X * w[:, None], Y * w, rcond=None)
    b, c = coef
    resid = Y - X @ coef
    rmse = float(np.sqrt(np.average(resid ** 2, weights=W))) * TRADING_DAYS
    return float(b), float(c), resid, rmse, rows


def model_daily(d, L, er, b, c, div):
    if d not in r_ndx or d not in rate:
        return None
    return (L * r_ndx[d] + div[d] - er / TRADING_DAYS
            - b * (L - 1) * rate[d] - c * (L - 1) * abs(r_ndx[d]))


def main():
    print("=" * 92)
    print("1) 계수 확정 (a=0 고정, 보수적)")
    print("=" * 92)
    div = ndx_div_series(dates, pre2004=0.005)
    rows = annual_rows(div)
    b, c, resid, rmse, rows = fit_bc(rows)
    print(f"  b (조달금리 계수) = {b:.5f}    실효조달금리 = T-bill(BEY) x {b:.4f}")
    print(f"  c (변동성 계수)   = {c:.6f}")
    print(f"  가중 RMSE = {rmse*100:.3f}%p/년")

    # 상품별 연도 잔차 요약
    for sym in ("qqq", "qld", "tqqq"):
        idx = [i for i, r in enumerate(rows) if r[0] == sym]
        v = np.array([resid[i] for i in idx]) * TRADING_DAYS
        print(f"    {sym.upper():5s} 연도잔차: 평균 {v.mean()*100:+.3f}%p  "
              f"표준편차 {v.std()*100:.3f}%p  최악 {v.min()*100:+.2f}%p  최고 {v.max()*100:+.2f}%p")

    print("\n" + "=" * 92)
    print("2) 누적 검증 (모델만으로 전 기간 재현)")
    print("=" * 92)
    for sym in ("qqq", "qld", "tqqq"):
        L, er = LEV[sym], ER[sym]
        lev = load_series(sym, "adjclose"); r = daily_returns(lev)
        ds = [d for d in sorted(r) if model_daily(d, L, er, b, c, div) is not None]
        ga = gm = 1.0
        for d in ds:
            ga *= 1 + r[d]; gm *= 1 + model_daily(d, L, er, b, c, div)
        n = len(ds)
        aa = ga ** (TRADING_DAYS / n) - 1
        mm = gm ** (TRADING_DAYS / n) - 1
        print(f"  {sym.upper():5s} {ds[0]}~{ds[-1]}  실제 연{aa*100:7.3f}%  모델 연{mm*100:7.3f}%  "
              f"차이 {(aa-mm)*100:+6.3f}%p   최종배수 {ga:9.2f} / {gm:<9.2f}")

    print("\n" + "=" * 92)
    print("3) 1985~2003 배당 가정 민감도 (가상 TQQQ 1985~1999 구간 CAGR)")
    print("=" * 92)
    for pre in (0.003, 0.005, 0.008):
        dv = ndx_div_series(dates, pre2004=pre)
        g = 1.0; n = 0
        for d in dates:
            if d >= "1999-01-01": break
            v = model_daily(d, 3, ER["tqqq"], b, c, dv)
            if v is not None:
                g *= 1 + v; n += 1
        print(f"  배당 {pre*100:.1f}%/년 -> 1985~1998 가상TQQQ 누적 {g:10.2f}배, "
              f"CAGR {(g**(TRADING_DAYS/n)-1)*100:6.2f}%  ({n}일)")

    # ---------------- 시계열 생성 ----------------
    print("\n" + "=" * 92)
    print("4) 시계열 생성")
    print("=" * 92)
    real = {s: daily_returns(load_series(s, "adjclose")) for s in ("tqqq", "qqq")}

    out = []
    lv = {"tqqq": 100.0, "qqq": 100.0, "ndx": 100.0}
    src_count = {"tqqq": {"model": 0, "real": 0}, "qqq": {"model": 0, "real": 0}}
    first = True
    for d in dates:
        if d not in r_ndx or d not in rate:
            continue
        row = {"date": d}
        if not first:
            lv["ndx"] *= 1 + r_ndx[d]
        for sym in ("tqqq", "qqq"):
            L, er = LEV[sym], ER[sym]
            if d >= REAL_START[sym] and d in real[sym]:
                rr = real[sym][d]; s = "real"
            else:
                rr = model_daily(d, L, er, b, c, div); s = "model"
            if rr is None:
                rr = 0.0
            if not first:
                lv[sym] *= 1 + rr
            src_count[sym][s] += 1
            row[sym] = lv[sym]
            row[sym + "_src"] = s
        row["ndx"] = lv["ndx"]
        row["rate"] = irx_ff[d]
        row["div"] = div[d] * TRADING_DAYS
        out.append(row)
        first = False

    path = "data/series.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("date,ndx,tqqq,qqq,rate_pct,div_annual,tqqq_src,qqq_src\n")
        for r in out:
            f.write(f"{r['date']},{r['ndx']:.6f},{r['tqqq']:.6f},{r['qqq']:.6f},"
                    f"{r['rate']:.4f},{r['div']:.6f},{r['tqqq_src']},{r['qqq_src']}\n")
    print(f"  {path}  {len(out)}행  {out[0]['date']} ~ {out[-1]['date']}")
    for sym in ("tqqq", "qqq"):
        print(f"    {sym.upper():5s} 모델 {src_count[sym]['model']}일 / 실제 {src_count[sym]['real']}일")

    n = len(out)
    for sym in ("ndx", "tqqq", "qqq"):
        g = out[-1][sym] / 100.0
        print(f"    {sym.upper():5s} 1985-10-01=100 -> {out[-1][sym]:,.0f}   "
              f"CAGR {(g**(TRADING_DAYS/n)-1)*100:6.2f}%")

    with open("data/coef.txt", "w", encoding="utf-8") as f:
        f.write(f"b\t{b:.8f}\nc\t{c:.8f}\npre2004_div\t0.005\n")
    print("  data/coef.txt 저장")


if __name__ == "__main__":
    main()
