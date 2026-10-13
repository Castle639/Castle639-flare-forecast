# The first call (Sun room 25, 23:32 UTC 12 Oct 2026)
Written 2026-10-12 23:33 UTC, before 00:00 UTC 13 Oct. R9 and R10_d2 as frozen (`frozen/joint_R9.pkl` 03d00f71..., `frozen/joint_R10_d2.pkl` 17801afb...),
on SWPC's live primary GOES 0.1-0.8 nm X-rays before 22:00 UTC of 12 Oct (the window [11 Oct 22:00, 12 Oct 22:00), `live/forward.py`),
beside SWPC's numbers from the RSGA issued at 2200Z on 12 Oct (`live/rsga_issued_2026-10-12_2200Z.txt`, sha256 e024ad6a6c426805a8a73cf54cdd257d88e54a4eb0f1615fd73107369b797896: "Class M 45/40/35").

| target day | ours | P(>= M1 flare day) | SWPC (RSGA 12 Oct 2200Z) |
|---|---|---|---|
| 13 Oct 2026 | R9 (day 1) | **0.165** | **0.45** (Class M, day 1) |
| 14 Oct 2026 | R10_d2 (day 2) | **0.170** | **0.40** (Class M, day 2) |

The Sun grades both: a day is an M day if the GOES 0.1-0.8 nm flux reaches 1e-5 W/m2 on it (UTC). The forward job
(`.github/workflows/sun-room25-forward.yml`, daily 22:17 UTC) grades them from 13 and 14 Oct on and issues every day after.
Features (log10 W/m2): xl_max24 -5.930, xl_mean24 -6.159, xl_min24 -6.403, xl_last -6.194, xl_max6 -5.975; hours since an M-level sample 54.1; window coverage 0.979.
