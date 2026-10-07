# -*- coding: utf-8 -*-
"""회귀 대신 누적성과를 직접 비교해 실제 총비용을 잰다."""
import numpy as np
from common import load_series, irx_to_daily_rate, forward_fill, TRADING_DAYS
from model import ndx_div_series, daily_returns

ndx = load_series("ndx", "close")
irx = load_series("irx", "close")
r_ndx = daily_returns(ndx)
irx_ff = forward_fill(irx, sorted(set(irx) | set(ndx)))
div = ndx_div_series(sorted(ndx))

def ann(g, n):
    return g ** (TRADING_DAYS / n) - 1.0 if n > 0 and g > 0 else float("nan")

for sym, L, er in (("tqqq", 3, 0.0084), ("qld", 2, 0.0095)):
    lev = load_series(sym, "adjclose")
    r_lev = daily_returns(lev)
    ds = [d for d in sorted(r_lev) if d in r_ndx and d in irx_ff]
    n = len(ds)

    g_act = 1.0          # 실제
    g_p3  = 1.0          # L*r_ndx 만 (비용 0)
    g_fin = 1.0          # L*r_ndx - (L-1)*rate
    g_all = 1.0          # + 배당(1배) - 운용보수
    for d in ds:
        r = r_ndx[d]; rt = irx_to_daily_rate(irx_ff[d]); dv = div[d]
        g_act *= 1 + r_lev[d]
        g_p3  *= 1 + L * r
        g_fin *= 1 + L * r - (L - 1) * rt
        g_all *= 1 + L * r - (L - 1) * rt + dv - er / TRADING_DAYS

    print(f"\n{'='*74}\n{sym.upper()}  (L={L}, 운용보수 {er*100:.2f}%)  {ds[0]} ~ {ds[-1]}  {n}일\n{'='*74}")
    print(f"  실제 누적배수            {g_act:12.4f}   연 {ann(g_act,n)*100:7.3f}%")
    print(f"  L*r_ndx (비용0)          {g_p3:12.4f}   연 {ann(g_p3,n)*100:7.3f}%")
    print(f"  - 조달비용               {g_fin:12.4f}   연 {ann(g_fin,n)*100:7.3f}%")
    print(f"  + 배당1배 - 운용보수     {g_all:12.4f}   연 {ann(g_all,n)*100:7.3f}%")
    print(f"\n  실제 vs 비용0    : 연 {(ann(g_act,n)-ann(g_p3,n))*100:+7.3f}%p  <- 실제 총비용")
    print(f"  실제 vs 조달반영 : 연 {(ann(g_act,n)-ann(g_fin,n))*100:+7.3f}%p")
    print(f"  실제 vs 완전모델 : 연 {(ann(g_act,n)-ann(g_all,n))*100:+7.3f}%p  <- 남은 설명 안 되는 부분")

    # 참고 수치
    avg_rate = float(np.mean([irx_to_daily_rate(irx_ff[d]) for d in ds])) * TRADING_DAYS
    avg_div  = float(np.mean([div[d] for d in ds])) * TRADING_DAYS
    vol = float(np.std([r_ndx[d] for d in ds])) * np.sqrt(TRADING_DAYS)
    print(f"\n  기간평균: 단기금리 {avg_rate*100:.3f}%  NDX배당 {avg_div*100:.3f}%  NDX변동성 {vol*100:.1f}%")
    print(f"  이론 변동성드래그 ~ (L^2-L)/2*vol^2 = {(L*L-L)/2*vol*vol*100:.2f}%/년")
