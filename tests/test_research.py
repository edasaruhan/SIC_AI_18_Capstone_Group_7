"""Checks aimed at leakage, timing, label integrity and trusted serialization."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from analysis.config import ROOT, F
from analysis.data import load_surveys, primary_cohort, window_features, routine_transitions
from analysis.train import inner_splits, fit_search, REFINED, linear_explanation
from deployment.inference import ResearchModel

def synthetic_record(start, end, timestamp=None, minutes=None):
    a, b = pd.Timestamp(start), pd.Timestamp(end)
    return {"pid": "fictional", "title_id": "fictional-title", "datetime_hour_start": a.floor("h"),
            "approximate_session_start": a, "approximate_session_end": b,
            "approximate_session_end_original": b, "timestamp": pd.Timestamp(timestamp) if timestamp else b,
            "minutes": (b-a).total_seconds()/60 if minutes is None else minutes}

def windows():
    return pd.DataFrame({"pid": ["fictional"], "start": pd.to_datetime(["2025-01-01T00:00Z"]), "end": pd.to_datetime(["2025-01-15T00:00Z"])})

def test_cutoff_requires_entire_record_and_known_timestamp():
    s = pd.DataFrame([
        synthetic_record("2025-01-14T23:00Z", "2025-01-15T01:00Z"),
        synthetic_record("2025-01-02T00:00Z", "2025-01-02T01:00Z", "2025-01-15T00:01Z"),
        synthetic_record("2025-01-14T23:00Z", "2025-01-15T00:00Z"),
        synthetic_record("2024-12-31T23:00Z", "2025-01-01T01:00Z")])
    f, retained = window_features(s, windows(), "strict")
    assert len(retained) == 1
    assert f.weekly_hours.iloc[0] == .5
    assert len(window_features(s, windows(), "legacy")[1]) == 3

def test_elapsed_day_allocation_conserves_minutes_across_week_boundary():
    s = pd.DataFrame([synthetic_record("2025-01-07T23:30Z", "2025-01-08T00:30Z")])
    f, _ = window_features(s, windows(), "strict")
    assert f.weekly_hours.iloc[0] == .5
    assert f.active_days.iloc[0] == 2
    assert f.max_minutes.iloc[0] == 30
    assert f.week_change.iloc[0] == 0

def test_absence_never_creates_a_nonplayer():
    s = pd.DataFrame([synthetic_record("2025-02-01T00:00Z", "2025-02-01T01:00Z")])
    assert window_features(s, windows(), "strict")[0].empty

@pytest.mark.integration
def test_intake_and_labels_reproduce_pinned_cohort():
    b, i, q = load_surveys()
    p = primary_cohort(q)
    assert (len(b), b.pid.nunique(), len(i), len(p)) == (6844, 1948, 33046, 710)
    assert not p.index.duplicated().any()
    assert p.baseline.between(4, 20).all() and p.target.between(4, 20).all()
    assert ((p.target > p.baseline).sum(), (p.target == p.baseline).sum(), (p.target < p.baseline).sum()) == (199, 136, 375)

def test_routine_sign_and_actual_date_gap():
    q = pd.DataFrame({"pid": ["fictional"]*3, "wave": [1, 2, 3],
                      "date": pd.to_datetime(["2025-01-01T00:00Z", "2025-01-14T23:59Z", "2025-01-29T00:00Z"]),
                      "gaming_value_routines": [-3, 2, 0]})
    r = routine_transitions(q)
    assert r.baseline.tolist() == [3, -2]
    assert r.target.tolist() == [-2, 0]
    assert r.gap_days.ge(14).tolist() == [False, True]

def test_skipped_wave_is_not_next_survey_pair():
    q = pd.DataFrame({"pid": ["fictional"]*2, "wave": [1, 3],
                      "date": pd.to_datetime(["2025-01-01T00:00Z", "2025-01-29T00:00Z"]), "gaming_value_routines": [0, 1]})
    assert routine_transitions(q).empty

def test_repeated_people_are_separate_in_every_inner_split():
    groups = np.repeat(np.arange(12), 3)
    for train, test in inner_splits(pd.DataFrame({"a": groups}), groups):
        assert not set(groups[train]) & set(groups[test])

def test_preprocessing_uses_only_training_rows_and_shap_is_additive():
    x = pd.DataFrame({"baseline": [4, 5, 6, 7, 8, 9, 10, 11, 12], "weekly_hours": [1, 2, 3, 4, 5, 6, 7, 8, 9]})
    y = np.arange(9) + 4.
    search = fit_search(REFINED["R_M2"], x, y, inner_splits(x))
    assert search.best_estimator_.named_steps['scale'].mean_.tolist() == [8., 5.]
    heldout = pd.DataFrame({"baseline": [1000], "weekly_hours": [2000]})
    _, error = linear_explanation(search.best_estimator_, x, heldout)
    assert error < 1e-8
    assert search.best_estimator_.named_steps['scale'].mean_.tolist() == [8., 5.]

def test_gdt_and_change_errors_agree_but_r_squared_need_not():
    from analysis.train import metrics
    y = np.array([4, 10, 8, 18]); base = np.array([4, 8, 9, 14]); pred = np.array([5, 9, 10, 15])
    a, b = metrics(y, pred), metrics(y-base, pred-base)
    assert a['MAE'] == b['MAE'] and a['RMSE'] == b['RMSE']
    assert a['R2'] != b['R2']

def test_artifact_tampering_fails_before_loading(tmp_path):
    m = json.loads((ROOT/'models/manifest.json').read_text())
    (tmp_path/'manifest.json').write_text(json.dumps(m))
    (tmp_path/m['artifact']).write_bytes(b'not a trusted artifact')
    with pytest.raises(ValueError, match='checksum'):
        ResearchModel(tmp_path)

def test_final_real_model_and_scenario_changes():
    m = ResearchModel()
    a, b, c = [m.predict(v) for v in ('example_a', 'example_b', 'example_c')]
    assert a['predicted_gdt_total'] != b['predicted_gdt_total']
    assert a['predicted_gdt_total'] != c['predicted_gdt_total']
    assert a['predicted_gdt_total'] == round(m.manifest['synthetic_8_12'], 4)

@pytest.mark.integration
def test_saved_results_match_original_report_and_final_people():
    r = json.loads((ROOT/'results/legacy.json').read_text())
    assert all(v['matches_4dp'] for row in r['reference_comparison'].values() for v in row.values())
    legacy = pd.read_csv(ROOT/'data/derived/primary_legacy.csv.gz')
    final = pd.read_csv(ROOT/'data/derived/primary_strict.csv.gz')
    assert legacy.pid.tolist() == final.pid.tolist()
    assert np.array_equal(legacy.target, final.target)
