# -*- coding: utf-8 -*-
"""
실제 TQQQ(2010~) / QLD(2006~) 로 레버리지 ETF 비용모델을 캘리브레이션한다.

모델:  r_lev(t) = L * r_ndx(t) - beta * rate_daily(t) - alpha
  L     : 레버리지 배수 (TQQQ=3, QLD=2)
  beta  : 조달비용 계수. 이론값 = L-1 (자기자본 1 초과분에만 조달비용)
  alpha : 일간 상수 마찰 (운용보수 + 추적오차 + 거래비용 + 배당효과 잔차)

회귀식:  y(t) = r_actual(t) - L*r_ndx(t) = -alpha - beta*rate_daily(t) + e
"""
import sys
from common import (load_series, irx_to_daily_rate, forward_fill,
                    ols2, TRADING_DAYS)


def build(symbol, L):
    ndx = load_series("ndx", "close")          # 가격지수
    lev = load_series(symbol, "adjclose")      # 배당·분할 조정 총수익
    irx = load_series("irx", "close")          # 13주 T-bill 할인율 %

    dates = sorted(set(ndx) & set(lev))
    irx_ff = forward_fill(irx, sorted(set(irx) | set(dates)))

    rows = []
    pn, pl = None, None
    for d in dates:
        n, l = ndx[d], lev[d]
        if pn is not None and pn > 0 and pl > 0:
            r_ndx = n / pn - 1.0
            r_lev = l / pl - 1.0
            rate = irx_ff.get(d)
            if rate is not None:
                rows.append((d, r_ndx, r_lev, irx_to_daily_rate(rate), rate))
        pn, pl = n, l
    return rows


def regress(rows, L, label):
    xs = [r[3] for r in rows]                       # rate_daily
    ys = [r[2] - L * r[1] for r in rows]            # 실제 - L*지수
    a, b, r2, n = ols2(xs, ys)
    alpha = -a
    beta = -b
    print(f"\n=== {label} (L={L}) ===")
    print(f"  표본 {n}일  {rows[0][0]} ~ {rows[-1][0]}")
    print(f"  beta  (조달비용 계수) = {beta:8.4f}   이론값 {L-1}")
    print(f"  alpha (일간 상수마찰) = {alpha*1e4:8.4f} bp/일  ->  연 {alpha*TRADING_DAYS*100:6.3f}%")
    print(f"  R^2 = {r2:.5f}")
    return alpha, beta


def regress_fixed_beta(rows, L, beta_fixed, label):
    """beta 를 이론값으로 고정하고 alpha 만 추정."""
    resid = [r[2] - L * r[1] + beta_fixed * r[3] for r in rows]
    alpha = -sum(resid) / len(resid)
    print(f"  [beta={beta_fixed} 고정] alpha = {alpha*1e4:7.4f} bp/일 -> 연 {alpha*TRADING_DAYS*100:6.3f}%  ({label})")
    return alpha


def by_bucket(rows, L, alpha, beta, keyfn, title):
    """구간별 잔차 평균 (모델이 편향돼 있는지)."""
    buckets = {}
    for r in rows:
        k = keyfn(r)
        pred = L * r[1] - beta * r[3] - alpha
        buckets.setdefault(k, []).append(r[2] - pred)
    print(f"\n  --- {title} ---")
    for k in sorted(buckets):
        v = buckets[k]
        m = sum(v) / len(v)
        print(f"    {str(k):>14s}  n={len(v):5d}  평균잔차 {m*1e4:+7.3f} bp/일  (연 {m*TRADING_DAYS*100:+6.2f}%)")


def main():
    print("=" * 78)
    print("레버리지 ETF 비용모델 캘리브레이션")
    print("=" * 78)

    results = {}
    for sym, L in (("tqqq", 3), ("qld", 2)):
        rows = build(sym, L)
        alpha, beta = regress(rows, L, sym.upper())
        alpha_fix = regress_fixed_beta(rows, L, L - 1, sym.upper())
        results[sym] = (rows, L, alpha, beta, alpha_fix)

        # 금리 구간별 편향 (beta 이론값 고정 모델로 평가)
        by_bucket(rows, L, alpha_fix, L - 1,
                  lambda r: f"{int(r[4])}~{int(r[4])+1}%" if r[4] < 6 else "6%+",
                  "금리 구간별 잔차 (beta 고정 모델)")
        # 연도별 편향
        by_bucket(rows, L, alpha_fix, L - 1,
                  lambda r: r[0][:4], "연도별 잔차 (beta 고정 모델)")

    print("\n" + "=" * 78)
    print("교차 확인: 두 상품의 alpha 가 비슷하면 구조가 일관된 것")
    print("=" * 78)
    for sym, (rows, L, alpha, beta, alpha_fix) in results.items():
        print(f"  {sym.upper():5s} L={L}  beta추정={beta:6.3f}(이론 {L-1})  "
              f"alpha(고정)= 연 {alpha_fix*TRADING_DAYS*100:5.3f}%")


if __name__ == "__main__":
    main()
