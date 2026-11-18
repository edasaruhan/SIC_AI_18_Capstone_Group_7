"""Cohort construction and two explicitly different timing interpretations.

legacy reproduces the submitted code, including its starting-hour allocation.
strict uses whole approximate records, known by the cutoff, split across elapsed
24-hour bins. Approximate intervals do not establish true active-play sessions.
"""
import numpy as np
import pandas as pd
from .config import DATA, GDT, F

SURVEY_COLS = ["pid", "wave", "date", *[f"gdt_{k}" for k in range(1, 5)],
               *[f"gaming_value_{k}" for k in ("work", "social", "cognitive", "emotion", "routines")]]
STEAM_COLS = ["pid", "title_id", "minutes", "minutes_original", "datetime_hour_start",
              "approximate_session_start", "approximate_session_end",
              "approximate_session_end_original", "timestamp"]

def load_surveys():
    b = pd.read_csv(DATA / "survey_biweekly.csv.gz", usecols=SURVEY_COLS, low_memory=False)
    i = pd.read_csv(DATA / "survey_intake.csv.gz", usecols=["pid", "qualified", "age"], low_memory=False)
    if b.duplicated(["pid", "wave"]).any() or i.pid.duplicated().any():
        raise ValueError("Non-unique join keys; no automatic deduplication is permitted")
    items = b[[f"gdt_{k}" for k in range(1, 5)]]
    unknown = set(items.stack().unique()) - set(GDT)
    if unknown:
        raise ValueError(f"Unknown GDT categories: {unknown}")
    b["gdt"] = items.apply(lambda c: c.map(GDT)).sum(axis=1, min_count=4)
    b["date"] = pd.to_datetime(b.date, utc=True, errors="coerce")
    q = b.merge(i, on="pid", validate="many_to_one")
    q = q[q.qualified.eq(True) & q.age.between(18, 40) & q.wave.between(1, 6)].copy()
    return b, i, q

def primary_cohort(q):
    p = q.pivot(index="pid", columns="wave", values="gdt")[[1, 6]].dropna()
    p.columns = ["baseline", "target"]
    p = p.join(q[q.wave.eq(1)].set_index("pid")[["date"]])
    p = p.join(q[q.wave.eq(6)].set_index("pid")[["date"]].rename(columns={"date": "target_date"}))
    if not (p.target_date > p.date + pd.Timedelta(days=14)).all():
        raise ValueError("GDT target must be measured after the prediction cutoff")
    return p.sort_index()

def load_steam():
    s = pd.read_csv(DATA / "steam.csv.gz", usecols=STEAM_COLS)
    for name in [n for n in STEAM_COLS if n not in ("pid", "title_id", "minutes", "minutes_original")]:
        s[name] = pd.to_datetime(s[name], utc=True, errors="coerce")
    return s

def select_records(s, start, mode):
    """s already joined to windows, with start/end columns per row."""
    if mode == "legacy":
        mask = (s.datetime_hour_start >= start) & (s.datetime_hour_start + pd.Timedelta(hours=1) <= s["end"])
    elif mode == "strict":
        mask = ((s.datetime_hour_start >= start)
                & (s.datetime_hour_start + pd.Timedelta(hours=1) <= s["end"])
                & (s.approximate_session_start >= start)
                & (s.approximate_session_end > s.approximate_session_start)
                & (s.approximate_session_end <= s["end"])
                & (s.approximate_session_end_original <= s["end"])
                & (s.timestamp <= s["end"])
                & (s.minutes > 0) & np.isfinite(s.minutes))
    else:
        raise ValueError(mode)
    return s.loc[mask].copy()

def window_features(s, windows, mode="strict"):
    """Return features for windows with >=1 retained record; no coverage claim.

    windows: unique index window_id, pid, start, end. A repeated person's windows
    remain separate. Columns never use the outcome or the subsequent survey.
    """
    w = windows.reset_index(names="window_id")
    joined = s.merge(w, on="pid", how="inner", validate="many_to_many")
    rows = select_records(joined, joined.start, mode)
    keys = pd.Index(sorted(rows.window_id.unique()), name="window_id")
    daily = pd.DataFrame(0., index=keys, columns=range(14))
    if not len(rows):
        return pd.DataFrame(columns=F[1:]), rows
    if mode == "legacy":
        rows["day"] = np.floor((rows.datetime_hour_start - rows.start).dt.total_seconds() / 86400).astype(int)
        a = rows.groupby(["window_id", "day"]).minutes.sum().unstack().reindex(index=keys, columns=range(14)).fillna(0)
        daily.loc[:, :] = a.to_numpy()
    else:
        lo = (rows.approximate_session_start - rows.start).dt.total_seconds().to_numpy()
        hi = (rows.approximate_session_end - rows.start).dt.total_seconds().to_numpy()
        minutes = rows.minutes.to_numpy()
        ids = daily.index.get_indexer(rows.window_id)
        for d in range(14):
            overlap = np.maximum(0, np.minimum(hi, (d + 1) * 86400) - np.maximum(lo, d * 86400))
            np.add.at(daily[d].values, ids, minutes * overlap / (hi - lo))
        if not np.isclose(daily.values.sum(), rows.minutes.sum(), atol=1e-5):
            raise AssertionError("Minute conservation failed")
    features = pd.DataFrame(index=keys)
    features["weekly_hours"] = daily.sum(axis=1) / 120
    features["active_days"] = daily.gt(0).sum(axis=1)
    features["sd_minutes"] = daily.std(axis=1, ddof=1)
    features["max_minutes"] = daily.max(axis=1)
    features["week_change"] = (daily.iloc[:, 7:].sum(axis=1) - daily.iloc[:, :7].sum(axis=1)) / 60
    return features, rows

def primary_features(s, p, mode):
    windows = p.reset_index()[["pid", "date"]].rename(columns={"date": "start"})
    windows["end"] = windows.start + pd.Timedelta(days=14)
    f, rows = window_features(s, windows, mode)
    x = p.reset_index().join(f, how="inner")
    x = x.sort_values("pid").reset_index(drop=True)
    return x, rows

def routine_transitions(q):
    r = q.sort_values(["pid", "wave"]).copy()
    values = pd.to_numeric(r.gaming_value_routines, errors="coerce")
    if not values.dropna().between(-3, 3).all():
        raise ValueError("Unexpected clean routine coding")
    r["baseline"] = -values
    group = r.groupby("pid", sort=False)
    r["target"] = group.baseline.shift(-1)
    r["target_date"] = group.date.shift(-1)
    r["next_wave"] = group.wave.shift(-1)
    r["gap_days"] = (r.target_date - r.date).dt.total_seconds() / 86400
    r = r[(r.next_wave == r.wave + 1) & r.baseline.notna() & r.target.notna()].copy()
    return r.reset_index(drop=True)

def secondary_features(s, transitions):
    r = transitions[transitions.gap_days.ge(14)].reset_index(drop=True)
    windows = r[["pid", "date"]].rename(columns={"date": "end"}).copy()
    windows["start"] = windows.end - pd.Timedelta(days=14)
    f, rows = window_features(s, windows, "strict")
    x = r.join(f, how="inner").reset_index(drop=True)
    return x, rows
