# ETF 거시경제 자동 수집 품질 점검

- 품질 상태: **WARN**
- 미국 시장 기준일: 2026-11-06
- 점검 시각 UTC: 2026-11-06T23:58:52.139534+00:00
- 거시 수집 생성 시각 UTC: 2026-11-06T23:58:52.053606+00:00
- 기술 데이터 생성 시각 UTC: 2026-11-06T23:58:49.251747+00:00
- 요청/수집/시차 기준 정상: **22 / 20 / 20**

## 분야별 수집 상태

| 분야 | 정상 | 요청 | 누락 또는 오래됨 |
|---|---:|---:|---|
| treasury | 4 | 4 | - |
| inflation | 4 | 4 | - |
| labor | 6 | 6 | - |
| energy | 2 | 2 | - |
| volatility | 2 | 2 | - |
| foreign_exchange | 2 | 2 | - |
| money_markets | 0 | 2 | EFFR, SOFR |

## 발견한 문제

- Macro status is partial, not ok
- Missing required series: EFFR, SOFR
- Source failures: 2
- Critical market series not current: EFFR

## 원출처 오류

- EFFR: RuntimeError: JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- SOFR: RuntimeError: JSONDecodeError: Expecting value: line 1 column 1 (char 0)

## 사용 시 주의

- 수집 수치는 지표별 관측일과 발표일이 다를 수 있고 수정될 수 있음.
- 하이일드 회사채 ETF 가격수익률 차이는 실제 신용스프레드/OAS가 아님.
- 보유계좌·현금·개인 수익률은 공개 저장소에 기록하지 않음.
