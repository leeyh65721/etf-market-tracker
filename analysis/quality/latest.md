# ETF technical screen prospective accuracy audit

> **Not investment recommendations or a trading backtest.**
- Latest locked US session: **2026-10-20**
- Verified universe coverage: **96.0%**
- Preserved NYSE sessions: **1**
- Recorded new candidate transitions: **0**
- New locked baseline created on this execution: **False**
- Audit status (data quality only): **OK**

## Observation-to-observation results

| Holding window | Signals | Observed | Awaiting maturity | Unverifiable | Beat SPY | Mean excess | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
|5 NYSE sessions|0|0|0|0|0/0|n/a|insufficient_observations|
|10 NYSE sessions|0|0|0|0|0/0|n/a|insufficient_observations|
|20 NYSE sessions|0|0|0|0|0/0|n/a|insufficient_observations|

## Freshness and quality concerns

- None identified in the mechanical check.

## Evaluation rules

- NYSE trading calendar is used, not calendar or weekday approximations.
- Capture is frozen at first successful GitHub publishing day; same-day reruns do not overwrite the locked baseline.
- Only NEW technical-candidate transitions after a known consecutive prior NYSE session are evaluated. First archived session only seeds the baseline.
- Signal becomes known AFTER its market-session close; entry reference = the NEXT NYSE session CLOSE; exit reference = exact 5/10/20 NYSE sessions after this.
- If the reference day is missing, result is explicitly unverifiable, never interpolated.
- Relative return uses frozen Yahoo auto-adjusted close snapshots; corporate actions and later provider revisions can distort comparability.
- Technical labels are not ChatGPT investment recommendations; no actual portfolio, orders, FX, costs or P&L.
- Until enough future observations mature, there is **no supported predictive accuracy estimate**.
