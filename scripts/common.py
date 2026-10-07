# -*- coding: utf-8 -*-
"""데이터 로딩과 공통 계산."""
import os
import csv
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")

TRADING_DAYS = 252.0


def load_series(name, col="adjclose"):
    """data/raw/<name>.csv -> {date(str): float}"""
    path = os.path.join(RAW, f"{name}.csv")
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = row[col]
            if v == "" or v is None:
                continue
            out[row["date"]] = float(v)
    return out


def irx_to_daily_rate(pct):
    """
    ^IRX 는 13주 T-bill 의 '할인율'(annualized discount, %) 이다.
    채권등가수익률(BEY)로 바꾼 뒤 일할한다.
        BEY = 365*d / (360 - 91*d)
    저금리에선 차이가 미미하지만 1980~90년대 고금리 구간에선 무시할 수 없다.
    """
    d = pct / 100.0
    denom = 360.0 - 91.0 * d
    if denom <= 0:
        bey = d
    else:
        bey = 365.0 * d / denom
    return bey / TRADING_DAYS


def simple_returns(series, dates):
    """dates 순서대로 단순수익률. 첫날은 None."""
    out = {}
    prev = None
    for d in dates:
        v = series.get(d)
        if v is None:
            continue
        if prev is not None and prev[1] > 0:
            out[d] = v / prev[1] - 1.0
        prev = (d, v)
    return out


def forward_fill(series, dates):
    """dates 전체에 대해 직전 값으로 채운 dict 를 만든다."""
    out = {}
    last = None
    for d in dates:
        if d in series:
            last = series[d]
        if last is not None:
            out[d] = last
    return out


def ann_return(total_growth, n_days):
    if n_days <= 0 or total_growth <= 0:
        return float("nan")
    return total_growth ** (TRADING_DAYS / n_days) - 1.0


def max_drawdown(values):
    peak = None
    mdd = 0.0
    for v in values:
        if peak is None or v > peak:
            peak = v
        if peak and peak > 0:
            dd = v / peak - 1.0
            if dd < mdd:
                mdd = dd
    return mdd


def ols2(xs, ys):
    """단순선형회귀 y = a + b*x. (a, b, r2, n) 반환."""
    n = len(xs)
    if n < 3:
        return float("nan"), float("nan"), float("nan"), n
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return float("nan"), float("nan"), float("nan"), n
    b = sxy / sxx
    a = my - b * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = (sxy ** 2 / (sxx * syy)) if syy > 0 else float("nan")
    return a, b, r2, n
