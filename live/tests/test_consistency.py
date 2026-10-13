"""Forward job test (23:30 UTC 12 Oct 2026): for forecast days inside both the live 7-day feed and lockbox 1 (scored by the opening from
NCEI science files), the live features into frozen R9 against the opening's own predictions. Usage: python3 -I test_consistency.py"""
import sys, os, pickle
import pandas as pd, numpy as np
D = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, D); sys.path.insert(0, os.path.join(D, 'live'))
import forward as FW
x5 = FW.xrs5(); op = pd.read_csv(os.path.join(D, 'out', 'joint', 'pred_lock1_R9.csv'), index_col=0, parse_dates=True)
fz = pickle.load(open(os.path.join(D, 'frozen', 'joint_R9.pkl'), 'rb'))
for d1 in [d for d in op.index if d - pd.Timedelta(hours=26) >= x5.index.min()]:
    row, cov = FW.feats(x5, d1); X = pd.DataFrame([row[FW.F9].values], columns=FW.F9).fillna(fz['median'][FW.F9])
    p = fz['model'].predict_proba(X)[:, 1][0]
    print(d1.date(), 'live %.4f opening %.4f |dp| %.4f coverage %.2f hrs_since_m %.1f' % (p, op.p_model[d1], abs(p - op.p_model[d1]), cov, row['hrs_since_m']))
