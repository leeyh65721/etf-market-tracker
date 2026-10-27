# ETF 자동 수집 종합 품질 상태

- 상태: **ERROR**
- 미국 시장 기준일: 2026-10-26 (최신 마감일 2026-10-26)
- 검증된 ETF: **309/353 (87.5%)**
- 공식 22개 지표: **22/22**
- 추가 10개 세부 지표: **4/10 자동 정상**
- ISM 2개 수동 확인, NFCI가 오래되면 최신값으로 사용하지 않음.
- 신규 주의/오류 코드: ETF_COVERAGE_WATCH, EXTRA_UNAVAILABLE_SP500_BREADTH, EXTRA_MULTIPLE_LOSSES

## 발견 문제

| 수준 | 코드 | 내용 |
|---|---|---|
|WARN|ETF_COVERAGE_WATCH|Verified ETF universe 309/353 (87.5%)|
|KNOWN|NFCI_NOT_LIVE|NFCI latest official CSV status=stale, requires permitted manual verification|
|WARN|EXTRA_UNAVAILABLE_DURABLE_NEW_ORDERS|Supplemental automatic metric DURABLE_NEW_ORDERS is unavailable; don't use as current|
|WARN|EXTRA_UNAVAILABLE_MFG_NEW_ORDERS|Supplemental automatic metric MFG_NEW_ORDERS is stale; don't use as current|
|WARN|EXTRA_UNAVAILABLE_SP500_BREADTH|Supplemental automatic metric SP500_BREADTH is unavailable; don't use as current|
|ERROR|EXTRA_MULTIPLE_LOSSES|At least 3/7 normally automated supplemental metrics failed: DURABLE_NEW_ORDERS, MFG_NEW_ORDERS, SP500_BREADTH|

## 모듈별 최신 상태

|모듈|상태|
|---|---|
|screen_audit|OK|
|macro_etf_links|available|
|industry_evidence|OK|
|judgment_archive|OK|

**기준:** 자동 수집 완료 자체가 발표자료·매매판단 정확도를 보장하지 않음. 변화가 확인되지 않은 지표를 '변화 없음'으로 처리하지 말 것.
개인 계좌/비중/손익 등은 공개 GitHub에 기록하지 않음.
