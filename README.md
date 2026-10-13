# Flare forecast

A daily probability of an M-class solar flare, from Domino Observatory: the chance that the GOES 1–8 Å X-ray flux reaches 1×10⁻⁵ W/m² (M1.0, NOAA's R1 radio blackout) on the next UT day (R9) and on the day after (R10_d2). Each model reads six numbers from the last day of GOES X-ray flux. No SWPC number goes in.

It runs here once a day at 22:17 UTC. Every call goes into `live/ledger.csv` before its day begins and is graded on the GOES flux when the day ends (`live/scoreboard.json`), with SWPC's issued M-class probability beside it.

## On years the models never saw

Fitted on 1996–2024 and frozen, then scored once on two periods outside it. Brier score, lower is better. SWPC's is its issued M-class probability for the same day, from its daily report (RSGA).

| Model | Period | Days | M days | Ours | SWPC |
|---|---|---|---|---|---|
| R9, day 1 | 1986-01-01 – 1995-05-31 | 3,240 | 928 | 0.1262 | 0.1351 |
| R9, day 1 | 2025-01-01 – 2026-10-10 | 643 | 236 | 0.1846 | 0.2098 |
| R10_d2, day 2 | 1986-01-01 – 1995-05-30 | 3,239 | 930 | 0.1353 | 0.1457 |
| R10_d2, day 2 | 2025-01-01 – 2026-10-09 | 642 | 237 | 0.2014 | 0.2274 |

On both periods both models also beat calibrated persistence (a logistic on the day's peak flux). Every difference's paired interval sits above zero: 98.75 %, 27-day blocks bootstrapped, four candidates opened together. On 1986–95, R9 also beats SWPC with the M days taken from SWPC's own flare list: +0.0062 [+0.0008, +0.0118].

`python3 score.py` recomputes the table from `out/joint/`.

## Its limits
- 1986–95 is R9's blind test. R9 was designed after 2025–26 had been opened twice for an earlier model.
- On 2025–26, R9's margin over persistence is thin: +0.0128 [+0.0003, +0.0252].
- M1 is the everyday R1 level. It gives no X-class probability; an X-class version did not beat SWPC on 2017–24.
- The size: a Brier score 7–12 % below SWPC's.

## Files
- `frozen/`: the two models (scikit-learn pipelines, pickled) and their SHA-256 in `FREEZE.json`. A pickle runs code when loaded: check its hash first.
- `live/forward.py`: the daily job. `live/FIRST_CALL_2026-10-12.md`: its first call, for 13 and 14 Oct 2026.
- `out/joint/`: every day's prediction on both periods, beside SWPC's and the outcome. `joint_result.json`: the opening's full record, two proton candidates that failed included.
- `r1m_frozen.py`, `parse_rsga.py`, `lockbox.py`: the feature, report-parsing and date-guard code the job imports.

## Run it
    pip install -r requirements.txt
    python3 -I live/forward.py issue /tmp/try    # a call from the window that closed at 22:00 UTC
    python3 -I live/forward.py run               # grade, then issue, into live/
    python3 score.py

Data: SWPC's live GOES X-ray feed; NCEI's archive of SWPC's daily reports.

## Licence
BSD 3-Clause.
