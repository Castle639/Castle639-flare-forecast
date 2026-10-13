"""Sun room 25, the forward job (started 23:28 UTC 12 Oct 2026): R9 and R10_d2 frozen, run daily on live GOES X-rays, SWPC's
number beside, graded by the Sun. Model-free at run time: two frozen logistic pickles, no tokens.
  issue : after 22:00 UTC on day D, from SWPC's live 7-day primary GOES 0.1-0.8 nm feed (1-min, 5-min max as in training), the six
          R9 features over [D-1 22:00, D 22:00) (r1m_frozen.window_feats, hrs_since_m as build_frame): R9 -> P(>= M1 on D+1),
          R10_d2 -> P(>= M1 on D+2). SWPC's live 3-day-forecast R1-R2 for the same days is logged beside (reported only: issued 12:30).
  grade : for issued rows whose target day has ended: y = the day's max 0.1-0.8 nm flux >= 1e-5 (>= 50 % of 5-min slots), from the
          same feed; SWPC's comparator = the RSGA M probability as in development (the RSGA issued on d1-1: M1 for lead 1, M2 for lead 2),
          from NCEI once posted. Scoreboard: Brier of each model and of SWPC on the rows that have both.
Usage: python3 -I forward.py run|issue|grade [LIVE_DIR]   (run = grade then issue; LIVE_DIR defaults to sun/room25/live)"""
import sys, os, json, pickle, re, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
import numpy as np, pandas as pd
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, D)
import r1m_frozen as R
from parse_rsga import parse as parse_rsga
XR = "https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json"
TD = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"
RS = "https://www.ngdc.noaa.gov/stp/space-weather/swpc-products/daily_reports/reports_solar_geophysical_activity/{d:%Y}/{d:%m}/{d:%Y%m%d}RSGA.txt"
MODELS = {'R9': 1, 'R10_d2': 2}
F9 = ['xl_max24', 'xl_mean24', 'xl_min24', 'xl_last', 'xl_max6', 'hrs_since_m']
END = datetime(2027, 10, 12, tzinfo=timezone.utc)   # one year of forward days, then it stops by itself


def get(u, tries=3):
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "castle-sun-room25-forward"}), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
        except Exception:
            pass
    return None


def xrs5():
    d = json.loads(get(XR))
    # the science files' quality flag removes dropouts; the live feed's own flag is 'electron_contaminaton' (test 23:31: unflagged
    # dropouts to 1e-9..1e-8 pulled xl_min24 / xl_mean24 down and R9 up by ~0.15)
    s = pd.Series({pd.Timestamp(e['time_tag'][:16]): e['flux'] for e in d if e.get('energy') == '0.1-0.8nm' and e.get('flux') is not None
                   and not e.get('electron_contaminaton', False)}).sort_index()
    s = s.astype(float); s[s <= 0] = np.nan
    # eclipse-season dropouts (test 23:31: only xl_min24 differed, live -7.2..-7.6 vs science -6.2): the science files flag them; here a
    # 1-min sample > 0.5 dex below its rolling 1-h median is an instrument dropout (soft X-rays cannot fall 3x within minutes)
    med = s.rolling('60min', min_periods=10).median(); s[s < med * 10 ** -0.5] = np.nan
    return s.resample('5min').max().rename('xl')


def feats(x5, d1):
    F = R.window_feats(x5, 'xl')
    mt = x5[x5 >= 1e-5].index; iss = d1 - pd.Timedelta(hours=2)
    prior = mt[mt < iss]
    row = F.reindex([d1]).iloc[0].copy()
    row['hrs_since_m'] = min((iss - prior.max()).total_seconds() / 3600, 96.0) if len(prior) else 96.0
    win = x5[(x5.index >= iss - pd.Timedelta(hours=24)) & (x5.index < iss)]
    return row, float(win.notna().sum() / 288)


def r12(target):
    t = get(TD)
    if t is None: return None
    t = t.decode(errors='replace'); m = re.search(r'Radio Blackout Forecast for .*?\n\s*\n?\s*(.+?)\n\s*R1-R2\s+(.+?)\n', t, re.S)
    if not m: return None
    days = re.findall(r'(\w{3} \d{1,2})', m.group(1)); vals = re.findall(r'(\d+)%', m.group(2))
    for dstr, v in zip(days, vals):
        if pd.Timestamp(f"{dstr} {target.year}").date() == target.date(): return int(v) / 100
    return None


def ledger(L):
    p = os.path.join(L, 'ledger.csv')
    return (pd.read_csv(p, parse_dates=['issued', 'd1', 'target']) if os.path.exists(p) else pd.DataFrame()), p


def issue(L, now):
    d1 = pd.Timestamp((now - timedelta(hours=2)).date()) + pd.Timedelta(days=1)
    x5 = xrs5(); row, cov = feats(x5, d1)
    lg, lp = ledger(L); out = []
    for name, lead in MODELS.items():
        fz = pickle.load(open(os.path.join(D, 'frozen', f'joint_{name}.pkl'), 'rb'))
        X = pd.DataFrame([row[F9].values], columns=F9).fillna(fz['median'][F9])
        tgt = d1 + pd.Timedelta(days=lead - 1)
        if len(lg) and ((lg.model == name) & (lg.d1 == d1)).any(): continue
        out.append(dict(issued=pd.Timestamp(now.replace(tzinfo=None)), d1=d1, model=name, lead=lead, target=tgt, p=float(fz['model'].predict_proba(X)[:, 1][0]),
                        coverage=round(cov, 3), swpc_3day_r12=r12(tgt), y=np.nan, swpc_rsga=np.nan, **{f: float(row[f]) for f in F9}))
    if out:
        pd.concat([lg, pd.DataFrame(out)], ignore_index=True).to_csv(lp, index=False)
    return out


def grade(L, now):
    lg, lp = ledger(L)
    if not len(lg): return 0
    x5 = xrs5(); today = pd.Timestamp(now.date()); n = 0
    for i, r in lg.iterrows():
        t = pd.Timestamp(r['target'])
        if t >= today: continue
        if pd.isna(r['y']):
            day = x5[(x5.index >= t) & (x5.index < t + pd.Timedelta(days=1))]
            if day.notna().sum() >= 144: lg.at[i, 'y'] = float(day.max() >= 1e-5); n += 1
        if pd.isna(r['swpc_rsga']):
            iss = pd.Timestamp(r['d1']) - pd.Timedelta(days=1); b = get(RS.format(d=iss))
            if b is not None:
                tmp = os.path.join(L, '_rsga.txt'); open(tmp, 'wb').write(b)
                try:
                    q = parse_rsga(tmp); v = q.get(f"M{int(r['lead'])}") if q and q.get('d1') == str(pd.Timestamp(r['d1']).date()) else None
                    if v is not None: lg.at[i, 'swpc_rsga'] = v / 100
                finally:
                    os.remove(tmp)
    lg.to_csv(lp, index=False)
    sc = {'updated': now.strftime('%Y-%m-%dT%H:%MZ')}
    for name in MODELS:
        g = lg[(lg.model == name) & lg.y.notna()]; b = g[g.swpc_rsga.notna()]
        sc[name] = {'graded': int(len(g)), 'M_days': int(g.y.sum()), 'brier_model': float(((g.p - g.y) ** 2).mean()) if len(g) else None,
                    'with_swpc': int(len(b)), 'brier_model_same_rows': float(((b.p - b.y) ** 2).mean()) if len(b) else None,
                    'brier_swpc': float(((b.swpc_rsga - b.y) ** 2).mean()) if len(b) else None}
    json.dump(sc, open(os.path.join(L, 'scoreboard.json'), 'w'), indent=1)
    return n


if __name__ == '__main__':
    mode = sys.argv[1]; L = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, 'live'); os.makedirs(L, exist_ok=True)
    now = datetime.now(timezone.utc)
    if now > END: print('forward job ended', END.date()); sys.exit(0)
    if mode in ('grade', 'run'): print('graded', grade(L, now))
    if mode in ('issue', 'run'):
        if now.hour < 22 and mode == 'run': print('before 22:00 UTC: the window is not closed; nothing issued'); sys.exit(0)
        print('issued', issue(L, now))
