# -*- coding: utf-8 -*-
"""
적립식 Rolling Period 분석.
가능한 모든 시작월에 대해 같은 기간을 반복 시뮬레이션한다.
"""
import csv
from collections import defaultdict

rows = []
with open("data/series.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append((r["date"], float(r["tqqq"]), float(r["qqq"])))
dates = [r[0] for r in rows]
idx = {d: i for i, d in enumerate(dates)}

# 각 월의 첫 거래일
month_first = {}
for i, (d, _, _) in enumerate(rows):
    ym = d[:7]
    if ym not in month_first:
        month_first[ym] = i
months = sorted(month_first)


def simulate(i0, i1, init, monthly):
    """i0~i1 구간 적립식. (tqqq최종, qqq최종, 원금, tqqq MDD, qqq MDD)"""
    contrib_idx = {month_first[m] for m in months
                   if i0 < month_first[m] <= i1}
    units = {"t": init / rows[i0][1], "q": init / rows[i0][2]}
    principal = init
    peak = {"t": init, "q": init}
    mdd = {"t": 0.0, "q": 0.0}
    for i in range(i0, i1 + 1):
        if i in contrib_idx and monthly:
            units["t"] += monthly / rows[i][1]
            units["q"] += monthly / rows[i][2]
            principal += monthly
        vt = units["t"] * rows[i][1]
        vq = units["q"] * rows[i][2]
        for k, v in (("t", vt), ("q", vq)):
            if v > peak[k]:
                peak[k] = v
            dd = v / peak[k] - 1
            if dd < mdd[k]:
                mdd[k] = dd
    return units["t"] * rows[i1][1], units["q"] * rows[i1][2], principal, mdd["t"], mdd["q"]


def rolling(years, init, monthly):
    out = []
    need = years * 12
    for si, m in enumerate(months):
        ei = si + need
        if ei >= len(months):
            break
        i0 = month_first[m]
        i1 = month_first[months[ei]]
        t, q, p, mt, mq = simulate(i0, i1, init, monthly)
        out.append({"start": m, "end": months[ei], "tqqq": t, "qqq": q,
                    "principal": p, "mdd_t": mt, "mdd_q": mq})
    return out


def summarize(res, years, init, monthly, label):
    n = len(res)
    win = sum(1 for r in res if r["tqqq"] > r["qqq"])
    loss = n - win
    lose_principal = sum(1 for r in res if r["tqqq"] < r["principal"])
    print(f"\n{'='*104}")
    print(f"{label}  |  {years}년 적립식  초기 {init:,.0f} + 월 {monthly:,.0f}  |  시작월 {n}개 "
          f"({res[0]['start']} ~ {res[-1]['start']})")
    print(f"{'='*104}")
    print(f"  TQQQ 승 {win}회 ({win/n*100:.1f}%)   QQQ 승 {loss}회 ({loss/n*100:.1f}%)"
          f"   TQQQ 원금손실 {lose_principal}회 ({lose_principal/n*100:.1f}%)")

    ratios = sorted(res, key=lambda r: r["tqqq"] / r["qqq"])
    print(f"\n  --- TQQQ 가 QQQ 대비 최악이었던 시작월 5개 ---")
    for r in ratios[:5]:
        print(f"    {r['start']}~{r['end']}  원금 {r['principal']:>12,.0f}  "
              f"TQQQ {r['tqqq']:>14,.0f}  QQQ {r['qqq']:>14,.0f}  "
              f"비율 {r['tqqq']/r['qqq']:5.2f}  TQQQ MDD {r['mdd_t']*100:6.1f}%")
    print(f"  --- TQQQ 가 QQQ 대비 최고였던 시작월 3개 ---")
    for r in ratios[-3:]:
        print(f"    {r['start']}~{r['end']}  원금 {r['principal']:>12,.0f}  "
              f"TQQQ {r['tqqq']:>14,.0f}  QQQ {r['qqq']:>14,.0f}  "
              f"비율 {r['tqqq']/r['qqq']:5.2f}  TQQQ MDD {r['mdd_t']*100:6.1f}%")

    mults = sorted(r["tqqq"] / r["principal"] for r in res)
    qmults = sorted(r["qqq"] / r["principal"] for r in res)
    def pct(a, p):
        return a[min(len(a) - 1, int(len(a) * p))]
    print(f"\n  원금 대비 배수 분포 (TQQQ / QQQ)")
    for p, nm in ((0.0, "최악"), (0.1, "10%"), (0.25, "25%"), (0.5, "중앙"),
                  (0.75, "75%"), (0.9, "90%"), (0.999, "최고")):
        print(f"    {nm:5s}  TQQQ {pct(mults,p):8.2f}배   QQQ {pct(qmults,p):8.2f}배")
    worst = min(res, key=lambda r: r["tqqq"] / r["principal"])
    print(f"\n  TQQQ 최악 시작월: {worst['start']} -> {worst['end']}  "
          f"원금 {worst['principal']:,.0f} -> {worst['tqqq']:,.0f} "
          f"({worst['tqqq']/worst['principal']:.2f}배, {(worst['tqqq']/worst['principal']-1)*100:+.1f}%)")
    print(f"    같은 기간 QQQ: {worst['qqq']:,.0f} ({worst['qqq']/worst['principal']:.2f}배)")
    return res


def main(years=(10, 15, 20, 25, 30), init=100_000_000, monthly=1_500_000):
    """목적.md 예시 조건: 초기 1억, 월 150만."""
    for yrs in years:
        summarize(rolling(yrs, init, monthly), yrs, init, monthly, "적립식(초기+월납)")

    print("\n\n" + "#" * 104)
    print("# 참고: 월 적립 없이 일시금만")
    print("#" * 104)
    for yrs in (10, 15, 20):
        summarize(rolling(yrs, init, 0), yrs, init, 0, "일시금만")


if __name__ == "__main__":
    main()
