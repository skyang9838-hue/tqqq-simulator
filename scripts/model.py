# -*- coding: utf-8 -*-
"""
가상 TQQQ 비용모델의 정의와 캘리브레이션.

모델:
    r_lev(t) = L*r_ndx(t) + c_div*div(t) - beta*rate(t) - alpha - gamma*|r_ndx(t)|

  L      : 레버리지 배수
  div    : NDX 일간 배당수익률 (QQQ 실지급 배당에서 산출)
  c_div  : 배당 계수. 현물 보유분에서만 배당을 받으면 1, 전체 노출이면 L
  beta   : 조달비용 계수. 이론값 L-1
  alpha  : 일간 상수마찰 (운용보수 + 추적오차)
  gamma  : 리밸런싱 거래비용 (일간 |수익률| 에 비례)
"""
import csv
import os
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, RAW, TRADING_DAYS

QQQ_ER = 0.0020          # QQQ 운용보수 연 0.20%
PRE2004_NDX_DIV = 0.005  # 1985~2003 NDX 배당수익률 가정 (연). 민감도 분석 대상


def load_divs(name):
    path = os.path.join(RAW, f"{name}_div.csv")
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append((r["date"], float(r["amount"])))
    return sorted(out)


def ndx_div_series(dates, pre2004=PRE2004_NDX_DIV):
    """
    NDX 일간 배당수익률.
      2004~ : 직전 1년 QQQ 실지급 배당합 / QQQ 종가 + QQQ 운용보수
      ~2003 : 상수 가정 (QQQ 가 2003-12 이전엔 배당을 지급하지 않아 실측 불가)
    """
    qqq_c = load_series("qqq", "close")
    divs = load_divs("qqq")
    out = {}
    for d in dates:
        if d < "2004-06-30" or d not in qqq_c:
            out[d] = pre2004 / TRADING_DAYS
            continue
        y0 = f"{int(d[:4]) - 1}{d[4:]}"
        s = sum(a for dd, a in divs if y0 < dd <= d)
        px = qqq_c[d]
        out[d] = (s / px + QQQ_ER) / TRADING_DAYS if px > 0 else pre2004 / TRADING_DAYS
    return out


def daily_returns(series):
    ds = sorted(series)
    out = {}
    prev = None
    for d in ds:
        v = series[d]
        if prev is not None and prev > 0:
            out[d] = v / prev - 1.0
        prev = v
    return out


def build_frame():
    ndx = load_series("ndx", "close")
    irx = load_series("irx", "close")
    dates = sorted(ndx)
    irx_ff = forward_fill(irx, sorted(set(irx) | set(dates)))
    r_ndx = daily_returns(ndx)
    div = ndx_div_series(dates)
    rate = {d: irx_to_daily_rate(irx_ff[d]) for d in dates if d in irx_ff}
    return r_ndx, div, rate


def calibrate(symbol, L, r_ndx, div, rate, c_div=None, fix_beta=None):
    """c_div=None 이면 회귀로 함께 추정, 숫자면 고정."""
    lev = load_series(symbol, "adjclose")
    r_lev = daily_returns(lev)
    ds = [d for d in sorted(r_lev) if d in r_ndx and d in div and d in rate]

    y = np.array([r_lev[d] - L * r_ndx[d] for d in ds])
    cols, names = [], []
    cols.append(np.ones(len(ds)));                      names.append("const")
    if c_div is None:
        cols.append(np.array([div[d] for d in ds]));    names.append("div")
    else:
        y = y - c_div * np.array([div[d] for d in ds])
    if fix_beta is None:
        cols.append(np.array([rate[d] for d in ds]));   names.append("rate")
    else:
        y = y + fix_beta * np.array([rate[d] for d in ds])
    cols.append(np.array([abs(r_ndx[d]) for d in ds])); names.append("absr")

    X = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ coef
    resid = y - pred
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum(resid ** 2)) / ss_tot if ss_tot > 0 else float("nan")

    p = dict(zip(names, coef))
    return {
        "dates": ds,
        "alpha": -p["const"],
        "c_div": p.get("div", c_div),
        "beta": -p.get("rate", -fix_beta if fix_beta is not None else float("nan")),
        "gamma": -p["absr"],
        "r2": r2,
        "resid": resid,
    }


def report(tag, res, L, er):
    a, cd, b, g = res["alpha"], res["c_div"], res["beta"], res["gamma"]
    print(f"\n--- {tag} (L={L}, 운용보수 {er*100:.2f}%) ---")
    print(f"  표본 {len(res['dates'])}일  {res['dates'][0]} ~ {res['dates'][-1]}")
    print(f"  c_div = {cd:7.3f}        (현물보유분만이면 1, 전체노출이면 {L})")
    print(f"  beta  = {b:7.4f}        (이론 {L-1}, 배율 {b/(L-1):.3f})")
    print(f"  alpha = {a*TRADING_DAYS*100:7.3f}%/년   운용보수 대비 {(a*TRADING_DAYS-er)*100:+.3f}%p")
    print(f"  gamma = {g:7.4f}        (일간 1% 변동당 {g*0.01*1e4:.2f} bp)")
    print(f"  R^2   = {res['r2']:.5f}")
    yb = {}
    for i, d in enumerate(res["dates"]):
        yb.setdefault(d[:4], []).append(res["resid"][i])
    ann = {k: float(np.mean(v)) * TRADING_DAYS for k, v in yb.items()}
    sd = float(np.std(list(ann.values())))
    srt = sorted(ann.items(), key=lambda kv: kv[1])
    print(f"  연도별 잔차 표준편차 {sd*100:.2f}%p | 최악 {srt[0][0]}:{srt[0][1]*100:+.2f}% "
          f"최고 {srt[-1][0]}:{srt[-1][1]*100:+.2f}%")
    return sd


def main():
    r_ndx, div, rate = build_frame()
    print("=" * 78)
    print("배당 계수 c_div 를 데이터가 말하게 한다 (자유 추정)")
    print("=" * 78)
    for sym, L, er in (("tqqq", 3, 0.0084), ("qld", 2, 0.0095)):
        res = calibrate(sym, L, r_ndx, div, rate, c_div=None, fix_beta=None)
        report(f"{sym.upper()} 자유추정", res, L, er)

    print("\n" + "=" * 78)
    print("c_div=1 고정 (현물보유분에서만 배당 수취 가설)")
    print("=" * 78)
    for sym, L, er in (("tqqq", 3, 0.0084), ("qld", 2, 0.0095)):
        res = calibrate(sym, L, r_ndx, div, rate, c_div=1.0, fix_beta=None)
        report(f"{sym.upper()} c_div=1", res, L, er)

    print("\n" + "=" * 78)
    print(f"c_div=L 고정 (전체 노출에서 배당 수취 가설)")
    print("=" * 78)
    for sym, L, er in (("tqqq", 3, 0.0084), ("qld", 2, 0.0095)):
        res = calibrate(sym, L, r_ndx, div, rate, c_div=float(L), fix_beta=None)
        report(f"{sym.upper()} c_div={L}", res, L, er)


if __name__ == "__main__":
    main()
