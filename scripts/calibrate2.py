# -*- coding: utf-8 -*-
"""
확장 캘리브레이션.

1) NDX 배당수익률을 QQQ 실측치로 직접 역산한다.
     QQQ총수익 = NDX가격수익 + NDX배당수익 - QQQ운용보수(0.20%)
   ->  NDX배당수익 = QQQ총수익 - NDX가격수익 + 0.20%/252

2) 레버리지 모델에 배당과 변동성 항을 넣고 회귀한다.
     r_lev = L*(r_ndx + div) - beta*rate - alpha - gamma*|r_ndx|
   |r_ndx| 항은 일일 리밸런싱 규모에 비례하는 거래비용을 잡는다.
"""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS

QQQ_ER = 0.0020   # QQQ 운용보수 연 0.20%


def series_frame():
    ndx = load_series("ndx", "close")
    qqq = load_series("qqq", "adjclose")
    tqqq = load_series("tqqq", "adjclose")
    qld = load_series("qld", "adjclose")
    irx = load_series("irx", "close")

    dates = sorted(ndx)
    irx_ff = forward_fill(irx, sorted(set(irx) | set(dates)))
    return ndx, qqq, tqqq, qld, irx_ff, dates


def daily_returns(series, dates):
    out = {}
    prev = None
    for d in dates:
        v = series.get(d)
        if v is None:
            continue
        if prev is not None and prev > 0:
            out[d] = v / prev - 1.0
        prev = v
    return out


def main():
    ndx, qqq, tqqq, qld, irx_ff, all_dates = series_frame()

    r_ndx = daily_returns(ndx, all_dates)
    r_qqq = daily_returns(qqq, sorted(qqq))
    r_tqqq = daily_returns(tqqq, sorted(tqqq))
    r_qld = daily_returns(qld, sorted(qld))

    # ---------- 1) NDX 배당수익률 역산 ----------
    print("=" * 78)
    print("1) NDX 배당수익률 역산 (QQQ 실측 기반)")
    print("=" * 78)
    common = sorted(set(r_ndx) & set(r_qqq))
    div_raw = {d: r_qqq[d] - r_ndx[d] + QQQ_ER / TRADING_DAYS for d in common}

    # 연도별 평균 배당수익률 (연율)
    byyear = {}
    for d, v in div_raw.items():
        byyear.setdefault(d[:4], []).append(v)
    print("  연도별 추정 배당수익률 (연율):")
    yr_div = {}
    for y in sorted(byyear):
        m = float(np.mean(byyear[y])) * TRADING_DAYS
        yr_div[y] = m
        print(f"    {y}  {m*100:6.3f}%   (n={len(byyear[y])})")

    overall = float(np.mean(list(div_raw.values()))) * TRADING_DAYS
    print(f"\n  1999~2026 전체 평균: {overall*100:.3f}%/년")

    early = [yr_div[y] for y in sorted(yr_div) if y <= "2003"]
    print(f"  1999~2003 평균     : {float(np.mean(early))*100:.3f}%/년"
          f"   <- 1985~1998 구간에 적용할 후보")

    # 롤링 1년 평균 배당 (일별) — 노이즈 완화
    cdates = common
    arr = np.array([div_raw[d] for d in cdates])
    win = 252
    roll = np.convolve(arr, np.ones(win) / win, mode="valid")
    roll_map = {cdates[i + win - 1]: float(roll[i]) for i in range(len(roll))}
    for i in range(win - 1):
        roll_map[cdates[i]] = float(np.mean(arr[:win]))

    # ---------- 2) 레버리지 모델 회귀 ----------
    print("\n" + "=" * 78)
    print("2) 레버리지 모델 회귀:  r_lev = L*(r_ndx+div) - beta*rate - alpha - gamma*|r_ndx|")
    print("=" * 78)

    for name, rlev, L, er in (("TQQQ", r_tqqq, 3, 0.0084), ("QLD", r_qld, 2, 0.0095)):
        ds = [d for d in sorted(rlev) if d in r_ndx and d in roll_map and irx_ff.get(d) is not None]
        y = np.array([rlev[d] - L * (r_ndx[d] + roll_map[d]) for d in ds])
        X = np.column_stack([
            np.ones(len(ds)),                                     # -alpha
            np.array([irx_to_daily_rate(irx_ff[d]) for d in ds]),  # -beta
            np.array([abs(r_ndx[d]) for d in ds]),                 # -gamma
        ])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        alpha, beta, gamma = -coef[0], -coef[1], -coef[2]
        pred = X @ coef
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

        print(f"\n--- {name} (L={L}, 실제 운용보수 {er*100:.2f}%) ---")
        print(f"  표본 {len(ds)}일  {ds[0]} ~ {ds[-1]}")
        print(f"  alpha = {alpha*TRADING_DAYS*100:7.3f}%/년   (운용보수 {er*100:.2f}% 대비 "
              f"{(alpha*TRADING_DAYS-er)*100:+.3f}%p)")
        print(f"  beta  = {beta:7.4f}       (이론 {L-1}, 배율 {beta/(L-1):.3f})")
        print(f"  gamma = {gamma:7.4f}       (일간 |수익률| 1%당 {gamma*0.01*1e4:.3f} bp 추가비용)")
        print(f"  R^2   = {r2:.5f}")

        # 연도별 잔차
        resid = y - pred
        ybucket = {}
        for i, d in enumerate(ds):
            ybucket.setdefault(d[:4], []).append(resid[i])
        print("  연도별 잔차(연율):", end=" ")
        worst = sorted(((float(np.mean(v)) * TRADING_DAYS, k) for k, v in ybucket.items()))
        print(" | ".join(f"{k}:{m*100:+.2f}%" for m, k in worst[:3]),
              " ... ", " | ".join(f"{k}:{m*100:+.2f}%" for m, k in worst[-3:]))
        sd = float(np.std([float(np.mean(v)) * TRADING_DAYS for v in ybucket.values()]))
        print(f"  연도별 잔차 표준편차: {sd*100:.2f}%p   (작을수록 모델이 안정적)")


if __name__ == "__main__":
    main()
