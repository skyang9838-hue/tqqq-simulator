# -*- coding: utf-8 -*-
"""생성된 시계열이 역사적으로 말이 되는지 점검."""
import csv
from common import TRADING_DAYS

rows = []
with open("data/series.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append({"date": r["date"], "ndx": float(r["ndx"]),
                     "tqqq": float(r["tqqq"]), "qqq": float(r["qqq"]),
                     "rate": float(r["rate_pct"]), "src": r["tqqq_src"]})

def seg(a, b, label):
    sub = [r for r in rows if a <= r["date"] <= b]
    if len(sub) < 2:
        print(f"  {label}: 데이터 없음"); return
    o, e = sub[0], sub[-1]
    n = len(sub)
    out = f"  {label:26s} {o['date']}~{e['date']} {n:5d}일 "
    for k in ("ndx", "tqqq", "qqq"):
        g = e[k] / o[k]
        out += f" {k.upper()}:{(g-1)*100:+9.1f}%"
    print(out)

def mdd(key, a=None, b=None):
    sub = [r for r in rows if (a is None or r["date"] >= a) and (b is None or r["date"] <= b)]
    peak = None; worst = 0.0; wd = ("", "")
    pd_ = ""
    for r in sub:
        v = r[key]
        if peak is None or v > peak:
            peak = v; pd_ = r["date"]
        dd = v / peak - 1
        if dd < worst:
            worst = dd; wd = (pd_, r["date"])
    return worst, wd

print("=" * 104)
print("주요 구간별 성과")
print("=" * 104)
seg("1985-10-02", "1990-12-31", "1985~1990")
seg("1991-01-01", "1994-12-31", "1991~1994")
seg("1995-01-01", "2000-03-10", "1995~닷컴고점(2000-03)")
seg("2000-03-10", "2002-10-09", "닷컴붕괴(00.03~02.10)")
seg("2002-10-09", "2007-10-31", "2002~2007 회복")
seg("2007-10-31", "2009-03-09", "금융위기(07.10~09.03)")
seg("2009-03-09", "2020-02-19", "2009~2020 강세장")
seg("2020-02-19", "2020-03-23", "코로나 폭락")
seg("2020-03-23", "2021-12-31", "코로나 회복")
seg("2022-01-01", "2022-12-31", "2022 긴축")
seg("2023-01-01", "2026-08-27", "2023~현재")

print("\n" + "=" * 104)
print("최대낙폭 (MDD)")
print("=" * 104)
for k in ("ndx", "tqqq", "qqq"):
    w, (p, t) = mdd(k)
    print(f"  {k.upper():5s} 전기간 MDD {w*100:8.2f}%   고점 {p} -> 저점 {t}")
print()
for k in ("tqqq", "qqq"):
    w, (p, t) = mdd(k, "2000-01-01", "2003-12-31")
    print(f"  {k.upper():5s} 닷컴구간 MDD {w*100:8.2f}%  고점 {p} -> 저점 {t}")

print("\n" + "=" * 104)
print("가상 TQQQ 가 바닥에서 얼마나 회복했나 (닷컴 저점 이후)")
print("=" * 104)
lo = min((r for r in rows if "2002-01-01" <= r["date"] <= "2003-12-31"), key=lambda r: r["tqqq"])
last = rows[-1]
print(f"  닷컴 저점 {lo['date']}  TQQQ={lo['tqqq']:.6f}  QQQ={lo['qqq']:.4f}")
print(f"  현재      {last['date']}  TQQQ={last['tqqq']:,.1f}  QQQ={last['qqq']:,.1f}")
print(f"  저점대비 회복배수: TQQQ {last['tqqq']/lo['tqqq']:,.0f}배   QQQ {last['qqq']/lo['qqq']:,.1f}배")

hi = max((r for r in rows if r["date"] <= "2000-12-31"), key=lambda r: r["tqqq"])
print(f"\n  닷컴 고점 {hi['date']}  TQQQ={hi['tqqq']:,.2f}")
print(f"  고점 대비 현재: TQQQ {last['tqqq']/hi['tqqq']:.2f}배  "
      f"(고점 회복에 걸린 기간을 확인)")
rec = [r for r in rows if r["date"] > hi["date"] and r["tqqq"] >= hi["tqqq"]]
if rec:
    print(f"  고점 회복일: {rec[0]['date']}  ({(int(rec[0]['date'][:4])-int(hi['date'][:4]))}년 걸림)")
else:
    print("  고점을 아직 회복하지 못함")

print("\n" + "=" * 104)
print("금리 환경 확인 (조달비용 입력)")
print("=" * 104)
for a, b in (("1985-10-02","1989-12-31"),("1990-01-01","1999-12-31"),
             ("2000-01-01","2009-12-31"),("2010-01-01","2021-12-31"),
             ("2022-01-01","2026-08-27")):
    sub = [r["rate"] for r in rows if a <= r["date"] <= b]
    print(f"  {a[:4]}~{b[:4]}  평균 13주 T-bill {sum(sub)/len(sub):5.2f}%  "
          f"최저 {min(sub):4.2f}%  최고 {max(sub):5.2f}%")
