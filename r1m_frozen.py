"""Room 25, candidate R1M (day-1 and day-3 probability of a >= M1 flare day): the frozen pipeline.
build_frame() is mos.py's feature code for route R1M, unchanged in substance, callable on any inputs.
Modes:
  check   : refit spec B on 1996-2016 and reproduce out/R1M_val_pred.csv (and R1M_d3) exactly
  freeze  : fit spec B on 1996-2024 (all development years) for lead 1 and 3; save models, medians, baselines
Usage: python3 -I r1m_frozen.py check|freeze RSGA.csv S1_DIR X_DIR KP.txt OUTDIR"""
import sys, os, json, pickle, hashlib
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

FIT_MEDIAN_END = '2011-01-01'   # mos.py: gaps filled with the 1996-2010 medians


def window_feats(series, name, log=True):
    s = series.copy()
    if log: s = np.log10(s.clip(lower=1e-9))
    key = (s.index + pd.Timedelta(hours=2)).normalize() + pd.Timedelta(days=1)
    g = s.groupby(key)
    f = pd.DataFrame({f'{name}_max24': g.max(), f'{name}_min24': g.min(), f'{name}_mean24': g.mean()})
    sh = s.index + pd.Timedelta(hours=2)
    last1 = s[sh.hour >= 23]; k1 = (last1.index + pd.Timedelta(hours=2)).normalize() + pd.Timedelta(days=1)
    f[f'{name}_last'] = last1.groupby(k1).mean()
    six = s[(sh.hour >= 17) & (sh.hour < 18)]; k6 = (six.index + pd.Timedelta(hours=2)).normalize() + pd.Timedelta(days=1)
    f[f'{name}_slope6'] = f[f'{name}_last'] - six.groupby(k6).mean()
    last6 = s[sh.hour >= 18]; k66 = (last6.index + pd.Timedelta(hours=2)).normalize() + pd.Timedelta(days=1)
    f[f'{name}_max6'] = last6.groupby(k66).max()
    return f


def lg(p):
    p = np.clip(p, 0.005, 0.995); return np.log(p / (1 - p))


def build_frame(rsga_p, P, X, XD, kp_p, lead):
    """P: 5-min protons (p10, p100); X: 5-min XRS (xl); XD: daily (m, cover). Returns d with FEAT, sw_M, y."""
    F = pd.concat([window_feats(P.p10, 'p10'), window_feats(P.p100, 'p100'), window_feats(X.xl, 'xl')], axis=1)
    mt = X.xl[X.xl >= 1e-5].index
    iss = F.index - pd.Timedelta(hours=2)
    pos = np.searchsorted(mt.values, iss.values) - 1
    F['hrs_since_m'] = np.where(pos >= 0, (iss.values - mt.values[np.clip(pos, 0, None)]) / np.timedelta64(1, 'h'), 96.0)
    F['hrs_since_m'] = F['hrs_since_m'].clip(upper=96)
    r = pd.read_csv(rsga_p); r['d1'] = pd.to_datetime(r['d1'])
    r = r.drop_duplicates('d1', keep='last').set_index('d1').sort_index()
    kp = {}
    for L in open(kp_p):
        if L.startswith('#') or not L.strip(): continue
        c = L.split(); kp[pd.Timestamp(int(c[0]), int(c[1]), int(c[2]))] = float(c[25])
    f107 = pd.Series(kp).sort_index()
    d = F.reindex(r.index)
    d['sw_M'] = r[f'M{lead}'] / 100; d['sw_X'] = r[f'X{lead}'] / 100; d['sw_P'] = r[f'P{lead}'] / 100
    d['f107'] = np.log(f107.shift(2).reindex(d.index).clip(lower=50))
    tgt = d.index + pd.Timedelta(days=lead - 1)
    d['y'] = XD.m.reindex(tgt).values; d['cover_t'] = XD.cover.reindex(tgt).values
    d = d[(d['cover_t'] >= 0.5)].dropna(subset=['y', 'sw_M'])
    for c in ('sw_M', 'sw_X', 'sw_P'): d['lg_' + c] = lg(d[c])
    feat = ['lg_sw_M', 'lg_sw_X', 'lg_sw_P', 'f107', 'hrs_since_m'] + [c for c in F.columns if c != 'hrs_since_m']
    return d, feat


def fit_B(tr, feat):
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=5000)).fit(tr[feat], tr.y)


if __name__ == '__main__':
    mode, rsga_p, s1d, xd, kp_p, out = sys.argv[1:7]
    P = pd.read_csv(os.path.join(s1d, 's1_5min.csv.gz'), index_col=0, parse_dates=True)
    X = pd.read_csv(os.path.join(xd, 'x_5min.csv.gz'), index_col=0, parse_dates=True)
    XD = pd.read_csv(os.path.join(xd, 'x_days.csv'), index_col=0, parse_dates=True)
    res = {}
    for lead in (1, 3):
        d, feat = build_frame(rsga_p, P, X, XD, kp_p, lead)
        d = d[(d.index + pd.Timedelta(days=lead - 1)) < pd.Timestamp('2025-01-01')]
        med = d[d.index < FIT_MEDIAN_END][feat].median()
        d[feat] = d[feat].fillna(med)
        if mode == 'check':
            tr = d[d.index < '2017-01-01']; va = d[d.index >= '2017-01-01']
            p = fit_B(tr, feat).predict_proba(va[feat])[:, 1]
            ref = pd.read_csv(os.path.join(out, 'R1M_val_pred.csv' if lead == 1 else 'R1M_d3_val_pred.csv'), index_col=0, parse_dates=True)
            same_days = bool((ref.index == va.index).all()) if len(ref) == len(va) else False
            res[lead] = {'n': len(va), 'same_days': same_days, 'max_abs_diff_p': float(np.max(np.abs(ref.p_model.values - p))) if same_days else None}
        else:
            m = fit_B(d, feat)
            persist = LogisticRegression(max_iter=2000).fit(d[['xl_max24']], d.y)
            pk = os.path.join(out, f'r1m_frozen_lead{lead}.pkl')
            pickle.dump({'model': m, 'feat': feat, 'median': med, 'persistence': persist, 'climatology': float(d.y.mean()),
                         'fit_days': [str(d.index.min().date()), str(d.index.max().date())], 'n': len(d)}, open(pk, 'wb'))
            lr = m.named_steps['logisticregression']; sc = m.named_steps['standardscaler']
            res[lead] = {'n': len(d), 'events': int(d.y.sum()), 'fit_days': [str(d.index.min().date()), str(d.index.max().date())],
                         'coef': dict(zip(feat, np.round(lr.coef_[0], 4).tolist())), 'intercept': float(lr.intercept_[0]),
                         'scaler_mean': dict(zip(feat, np.round(sc.mean_, 5).tolist())), 'pkl_sha256': hashlib.sha256(open(pk, 'rb').read()).hexdigest()}
    print(json.dumps(res, indent=1, default=str))
    json.dump(res, open(os.path.join(out, f'r1m_{mode}.json'), 'w'), indent=1, default=str)
