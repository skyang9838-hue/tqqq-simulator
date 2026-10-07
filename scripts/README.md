# scripts

## 재생성 파이프라인 (이 순서로 실행)

| 순서 | 파일 | 하는 일 |
|---|---|---|
| 1 | `fetch_data.py` | Yahoo에서 `^NDX`·TQQQ·QQQ·QLD·`^IRX` 를 받아 `data/raw/*.csv` 로 저장 |
| 2 | `build_series.py` | 계수를 재추정하고 1985~현재 가상 TQQQ/QQQ 시계열 `data/series.csv` 생성 |
| 3 | `export_web.py` | 시계열을 `data/web_data.json` 으로 압축 |
| 4 | `build_html.py` | 템플릿 + 데이터 + app.js → `시뮬레이터.html` |

```bash
PYTHONUTF8=1 python scripts/fetch_data.py
PYTHONUTF8=1 python scripts/build_series.py
PYTHONUTF8=1 python scripts/export_web.py
PYTHONUTF8=1 python scripts/build_html.py
```

`PYTHONUTF8=1` 없이 돌리면 한글 출력이 깨진다.

## 공용 모듈 (지우면 안 됨)

- `common.py` — 데이터 로딩, `^IRX` 할인율→채권등가수익률 변환, 회귀 유틸
- `model.py` — 배당 시계열 산출(`ndx_div_series`), 일간수익률. `build_series.py` 가 import 한다

## 분석 도구

- `rolling.py` — 적립식 Rolling Period 분석을 콘솔에서 실행. 웹 시뮬레이터와 같은 계산
- `inspect_series.py` — 생성된 시계열의 구간별 성과·MDD·금리 환경 점검
- `verify_app.js` — **app.js 를 최소 DOM 스텁 위에서 실제로 실행**해 화면에 나갈 숫자를 뽑고 Python 결과와 대조한다.
  `node scripts/verify_app.js`

## 검증 과정 기록 (재실행 불필요, 근거로 남김)

모델 계수를 어떻게 정했는지의 흔적이다. `작업 요약.md` 3절의 서술이 이 스크립트들의 출력에서 나왔다.

- `calibrate.py` — 첫 시도. 일간 회귀로 `beta`·`alpha` 추정 → R² 0.006 으로 계수가 불안정함을 확인
- `calibrate2.py` — 배당을 `adjclose` 역산으로 넣어봤다가 1999~2003 배당이 음수로 나오는 것을 발견
- `diag_div.py` — 그 원인 진단. QQQ 첫 배당이 2003-12-24 라는 것과 2000년 지수 데이터 이상치를 찾아냄
- `diag_cum.py` — 회귀 대신 누적성과 직접 비교로 실제 총비용 측정
- `diag_qqq.py` — QQQ(L=1)로 데이터·배당 계산 검증. 잔차가 `(L−1)` 에 정비례함을 발견해 조달금리가 원인임을 확정
- `calib_annual.py` — 연도별 집계 회귀로 전환 (R² 0.006 → 0.84). 최종 계수의 근거
- `final_model.py` — 상수 스프레드 모델. 전체 누적은 맞지만 고금리 구간이 틀어지는 것을 확인하고 폐기
