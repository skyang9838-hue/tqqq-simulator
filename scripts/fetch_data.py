# -*- coding: utf-8 -*-
"""
Yahoo Finance 에서 원본 시계열을 내려받아 data/raw/*.csv 로 저장한다.

FRED 는 이 네트워크에서 403 으로 차단되어 쓸 수 없다. 미국 단기금리는
^IRX (13주 T-bill 할인율, 1970~) 로 대체한다.
"""
import json
import os
import time
import urllib.request
import datetime as dt

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
}

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(HERE), "data", "raw")

# (야후 심볼, 저장 이름, 설명)
SERIES = [
    ("%5ENDX", "ndx",  "Nasdaq-100 price index"),
    ("TQQQ",   "tqqq", "ProShares UltraPro QQQ (3x)"),
    ("QQQ",    "qqq",  "Invesco QQQ Trust"),
    ("QLD",    "qld",  "ProShares Ultra QQQ (2x)"),
    ("%5EIRX", "irx",  "13-week T-bill discount rate (%)"),
]


def fetch_chart(symbol, tries=4):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1=0&period2=9999999999&interval=1d&events=div%2Csplit")
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:                      # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{symbol}: {type(last).__name__}: {last}")


def to_rows(payload):
    """야후 응답 -> [(YYYY-MM-DD, close, adjclose)] , 결측 제거."""
    res = payload["chart"]["result"][0]
    ts = res["timestamp"]
    quote = res["indicators"]["quote"][0]
    closes = quote["close"]
    adjblock = res["indicators"].get("adjclose")
    adjs = adjblock[0]["adjclose"] if adjblock else [None] * len(ts)

    rows = []
    for i, t in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue                                # 휴장/결측일은 버린다
        a = adjs[i] if i < len(adjs) else None
        d = dt.datetime.fromtimestamp(t, dt.UTC).date().isoformat()
        rows.append((d, c, a if a is not None else c))

    # 같은 날짜가 중복되면 뒤엣것을 남긴다
    dedup = {}
    for d, c, a in rows:
        dedup[d] = (c, a)
    return [(d, v[0], v[1]) for d, v in sorted(dedup.items())]


def dividends(payload):
    res = payload["chart"]["result"][0]
    evs = (res.get("events") or {}).get("dividends") or {}
    out = []
    for _, ev in evs.items():
        d = dt.datetime.fromtimestamp(ev["date"], dt.UTC).date().isoformat()
        out.append((d, ev["amount"]))
    return sorted(out)


def main():
    os.makedirs(RAW, exist_ok=True)
    summary = []
    for sym, name, desc in SERIES:
        payload = fetch_chart(sym)
        rows = to_rows(payload)
        path = os.path.join(RAW, f"{name}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("date,close,adjclose\n")
            for d, c, a in rows:
                f.write(f"{d},{c:.10g},{a:.10g}\n")

        divs = dividends(payload)
        if divs:
            dpath = os.path.join(RAW, f"{name}_div.csv")
            with open(dpath, "w", encoding="utf-8", newline="") as f:
                f.write("date,amount\n")
                for d, amt in divs:
                    f.write(f"{d},{amt:.10g}\n")

        summary.append((name, desc, len(rows), rows[0][0], rows[-1][0], len(divs)))
        print(f"[OK] {name:5s} {len(rows):6d} rows  {rows[0][0]} ~ {rows[-1][0]}  "
              f"divs={len(divs)}  ({desc})", flush=True)

    with open(os.path.join(RAW, "_manifest.txt"), "w", encoding="utf-8") as f:
        f.write(f"fetched_at\t{dt.datetime.now().isoformat(timespec='seconds')}\n")
        f.write("name\tdesc\trows\tstart\tend\tdivs\n")
        for s in summary:
            f.write("\t".join(str(x) for x in s) + "\n")
    print("\nsaved ->", RAW, flush=True)


if __name__ == "__main__":
    main()
