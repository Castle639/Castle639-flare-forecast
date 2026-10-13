"""Room 25: parse every RSGA into one row per issue: issue time, forecast dates (day 1..3),
M/X/proton probabilities, predicted Ap, mid- and high-latitude G probabilities, PCAF, observed F10.7.
Keyed by the forecast's own first date (room 11's lesson: RSGAs issued after midnight).
Usage: python3 -I parse_rsga.py RSGADIR OUT.csv"""
import sys, os, re, csv
from datetime import datetime, date, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lockbox import assert_dev

MON = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}


def three(s):
    v = re.findall(r'(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', s)
    return [int(x) for x in v[0]] if v else [None] * 3


def parse(path):
    T = open(path, errors='replace').read().upper()
    r = {}
    m = re.search(r'ISSUED[: ]*\s*(\d{4}) (\w{3}) (\d{1,2}) (\d{4}) UTC', T)
    if m:
        r['issued'] = datetime(int(m[1]), MON[m[2]], int(m[3]), int(m[4][:2]), int(m[4][2:])).isoformat()
    else:
        m = re.search(r'ISSUED AT (\d{4})Z ON (\d{1,2}) (\w{3}) (\d{4})', T)
        r['issued'] = datetime(int(m[4]), MON[m[3]], int(m[2]), int(m[1][:2]), int(m[1][2:])).isoformat() if m else ''
    m = re.search(r'EVENT PROBABILITIES\s+(\d{1,2}) (\w{3})', T)
    if not m: return None
    iss = datetime.fromisoformat(r['issued']) if r['issued'] else datetime.strptime(os.path.basename(path)[:8], "%Y%m%d")
    mon = MON[m[2]]; yr = iss.year + (1 if (mon == 1 and iss.month == 12) else 0)
    d1 = date(yr, mon, int(m[1]))
    r['d1'] = d1.isoformat()
    sec = T[m.start():]
    for key, pat in (('M', r'CLASS M\s+([\d/ ]+)'), ('X', r'CLASS X\s+([\d/ ]+)'), ('P', r'PROTON\s+([\d/ ]+)')):
        mm = re.search(pat, sec[:400]); v = three(mm[1]) if mm else [None] * 3
        for k in range(3): r[f'{key}{k+1}'] = v[k]
    mm = re.search(r'PCAF\s+(\w+)', sec[:400]); r['pcaf'] = mm[1] if mm else ''
    mm = re.search(r'OBSERVED\s+\d{1,2} \w{3}\s+(\d+)', T); r['f107'] = int(mm[1]) if mm else None
    mm = re.search(r'PREDICTED AFR/AP[^\n]*?(\d+)/(\d+)-(\d+)/(\d+)-(\d+)/(\d+)', T)
    for k in range(3): r[f'Ap{k+1}'] = int(mm[2 + 2 * k]) if mm else None
    mm = re.search(r'OBSERVED AFR/AP\s+\d{1,2} \w{3}\s+(\d+)/(\d+)', T); r['ApObsPrev'] = int(mm[2]) if mm else None
    mm = re.search(r'ESTIMATED AFR/AP\s+\d{1,2} \w{3}\s+(\d+)/(\d+)', T); r['ApEst'] = int(mm[2]) if mm else None
    g = T[T.find('GEOMAGNETIC ACTIVITY PROBABILITIES'):]
    mid = g[:g.find('HIGH LATITUDES')] if 'HIGH LATITUDES' in g else g
    hi = g[g.find('HIGH LATITUDES'):] if 'HIGH LATITUDES' in g else ''
    for tag, blk in (('mid', mid), ('hi', hi)):
        for key, pat in (('act', r'ACTIVE\s+([\d/ ]+)'), ('min', r'MINOR STORM\s+([\d/ ]+)'), ('maj', r'MAJOR-SEVERE STORM\s+([\d/ ]+)')):
            mm = re.search(pat, blk); v = three(mm[1]) if mm else [None] * 3
            for k in range(3): r[f'{tag}_{key}{k+1}'] = v[k]
    return r


if __name__ == '__main__':
    rows = []
    for fn in sorted(os.listdir(sys.argv[1])):
        if not fn.endswith('RSGA.txt'): continue
        try:
            r = parse(os.path.join(sys.argv[1], fn))
        except Exception as e:
            print('ERR', fn, e); continue
        if r is None: print('NOPROB', fn); continue
        r['file'] = fn; rows.append(r)
    # targets on or after the lockbox start (the 29-31 Dec 2024 issues' later days) are dropped by every scorer
    keys = list(rows[0].keys())
    with open(sys.argv[2], 'w', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
    print(len(rows), 'rows')
