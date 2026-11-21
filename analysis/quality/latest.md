# ETF technical screen prospective accuracy audit

> **Not investment recommendations or a trading backtest.**
- Latest locked US session: **2026-11-20**
- Verified universe coverage: **96.0%**
- Preserved NYSE sessions: **24**
- Recorded new candidate transitions: **78**
- New locked baseline created on this execution: **True**
- Audit status (data quality only): **OK**

## Observation-to-observation results

| Holding window | Signals | Observed | Awaiting maturity | Unverifiable | Beat SPY | Mean excess | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
|5 NYSE sessions|78|75|3|0|42/75|-0.691pp|exploratory_only|
|10 NYSE sessions|78|59|19|0|37/59|-0.622pp|exploratory_only|
|20 NYSE sessions|78|2|76|0|2/2|+5.147pp|insufficient_observations|

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
