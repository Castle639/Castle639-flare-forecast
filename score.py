"""Recomputes the README's table from the day-by-day predictions in out/joint/ (standard library only).
Brier score: the mean of (p - y)^2 over days; y = 1 on a day whose GOES 0.1-0.8 nm flux reaches 1e-5 W/m2 (M1.0)."""
import csv, os
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'joint')
print('model   period                    days  M days  model   SWPC    lower by')
for m in ('R9', 'R10_d2'):
    for k in (2, 1):
        r = list(csv.DictReader(open(os.path.join(D, f'pred_lock{k}_{m}.csv'))))
        y = [float(x['y']) for x in r]; n = len(r)
        bm = sum((float(x['p_model']) - v) ** 2 for x, v in zip(r, y)) / n
        bs = sum((float(x['p_swpc']) - v) ** 2 for x, v in zip(r, y)) / n
        print(f"{m:7} {r[0]['d1']} .. {r[-1]['d1']}  {n:5}  {int(sum(y)):6}  {bm:.4f}  {bs:.4f}  {100 * (bs - bm) / bs:4.1f} %")
