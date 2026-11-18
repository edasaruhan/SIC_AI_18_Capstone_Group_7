"""Build local-only feature tables and aggregate quality evidence."""
import json
import numpy as np
import pandas as pd
from .config import ROOT, RESULTS, prepare_dirs
from .data import load_surveys, primary_cohort, load_steam, primary_features, routine_transitions, secondary_features
from .download import sha256, FILES

def dump(name, value):
    (RESULTS / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

def approximate_hour_audit(s):
    """Allocate corrected approximate intervals, without calling them true play.

    This cannot undo provider aggregation/scaling. It diagnoses the approximation
    separately from assigning the full record to its starting hour.
    """
    start = s.approximate_session_start.astype('int64').to_numpy() / 1e9
    end = s.approximate_session_end.astype('int64').to_numpy() / 1e9
    hour = np.floor(start / 3600).astype('int64')
    frames = []
    for offset in range(int(np.ceil((end-start).max()/3600)) + 1):
        h = hour + offset
        overlap = np.maximum(0, np.minimum(end, (h+1)*3600) - np.maximum(start, h*3600))
        active = overlap > 0
        frames.append(pd.DataFrame({'pid': s.pid.to_numpy()[active], 'hour': h[active],
                                    'minutes': s.minutes.to_numpy()[active] * overlap[active] / (end[active]-start[active])}))
    h = pd.concat(frames, ignore_index=True).groupby(['pid','hour']).minutes.sum()
    d = h.reset_index().assign(day=lambda v: v.hour // 24).groupby(['pid','day']).minutes.sum()
    return {'approximate_allocated_person_hours': len(h), 'approximate_allocated_hours_gt60': int(h.gt(60+1e-6).sum()),
            'approximate_allocated_hour_max': float(h.max()), 'approximate_allocated_utc_days_gt1440': int(d.gt(1440+1e-6).sum()),
            'approximate_allocated_utc_day_max': float(d.max())}

def main():
    prepare_dirs()
    lock = json.loads((ROOT / "data/source_lock.json").read_text())
    for remote, path in FILES.items():
        if sha256(path) != lock["files"][remote]["sha256"]:
            raise ValueError(f"Source lock mismatch: {path.name}")
    b, i, q = load_surveys()
    p = primary_cohort(q)
    s = load_steam()
    raw_pivot = b[b.wave.between(1, 6)].pivot(index="pid", columns="wave", values="gdt")[[1, 6]].dropna()
    legacy, oldrows = primary_features(s, p, "legacy")
    final, newrows = primary_features(s, p, "strict")
    transitions = routine_transitions(q)
    rq2, rq2rows = secondary_features(s, transitions)
    for name, x in (("primary_legacy", legacy), ("primary_strict", final), ("secondary", rq2)):
        assert not x[['baseline','target']].isna().any().any()
        x.to_csv(ROOT / f"data/derived/{name}.csv.gz", index=False)
    byhour = s.groupby(["pid", "datetime_hour_start"]).minutes.sum()
    byday = s.assign(day=s.datetime_hour_start.dt.floor("D")).groupby(["pid", "day"]).minutes.sum()
    earlyhour = oldrows.groupby(["pid", "datetime_hour_start"]).minutes.sum()
    earlyday = oldrows.assign(day=oldrows.datetime_hour_start.dt.floor("D")).groupby(["pid", "day"]).minutes.sum()
    positive_duration = s.approximate_session_end > s.approximate_session_start
    chronological = s.sort_values(["pid", "approximate_session_start"]).copy()
    chronological["previous_latest_end"] = chronological.groupby("pid").approximate_session_end.transform(lambda v: v.cummax().shift())
    overlap = chronological.approximate_session_start < chronological.previous_latest_end
    duration_error = ((s.approximate_session_end - s.approximate_session_start).dt.total_seconds() / 60 - s.minutes).abs()
    missing_gdt = {str(int(wave)): int(frame.gdt.isna().sum()) for wave, frame in b.groupby("wave")}
    completebase = q[q.wave.eq(1) & q.gdt.notna()]
    completeids = set(p.index)
    attrition = {"eligible_valid_baseline": len(completebase),
                 "completer_baseline_mean": float(completebase[completebase.pid.isin(completeids)].gdt.mean()),
                 "noncompleter_baseline_mean": float(completebase[~completebase.pid.isin(completeids)].gdt.mean())}
    quality = {
        "survey": {"rows": len(b), "people": b.pid.nunique(), "duplicate_person_wave": int(b.duplicated(["pid", "wave"]).sum()),
                   "intake_rows": len(i), "intake_duplicate_pid": int(i.pid.duplicated().sum()),
                   "unmatched_intake_people": int(b.loc[~b.pid.isin(i.pid), "pid"].nunique()),
                   "unmatched_intake_rows": int((~b.pid.isin(i.pid)).sum()),
                   "missing_complete_gdt_by_wave": missing_gdt, "unparseable_dates": int(b.date.isna().sum()),
                   "off_schedule_rows": int((~b.wave.between(1, 6)).sum()), "attrition": attrition},
        "flow": {"both_gdt_before_eligibility": len(raw_pivot), "matched_to_intake": int(raw_pivot.index.isin(i.pid).sum()),
                 "eligible_gdt": len(p), "legacy_steam_people": len(legacy), "strict_steam_people": len(final),
                 "eligible_without_legacy_record": len(p) - len(legacy), "legacy_records": len(oldrows), "strict_records": len(newrows)},
        "gdt_change": {"increased": int((p.target > p.baseline).sum()), "same": int((p.target == p.baseline).sum()),
                       "decreased": int((p.target < p.baseline).sum()), "baseline_mean": float(p.baseline.mean()), "target_mean": float(p.target.mean())},
        "steam": {"rows": len(s), "people": s.pid.nunique(), "negative_minutes": int(s.minutes.lt(0).sum()),
                  "nonfinite_minutes": int((~np.isfinite(s.minutes)).sum()), "nonpositive_duration": int((~positive_duration).sum()),
                  "unparseable_timestamps": {c: int(s[c].isna().sum()) for c in s.select_dtypes(include='datetimetz').columns},
                  "duplicate_person_title_start": int(s.duplicated(["pid", "title_id", "approximate_session_start"]).sum()),
                  "duplicate_all_selected_fields": int(s.duplicated().sum()),
                  "individual_rows_minutes_gt60": int(s.minutes.gt(60).sum()),
                  "start_hour_sums_gt60": int(byhour.gt(60 + 1e-8).sum()), "start_hour_sum_max": float(byhour.max()),
                  "utc_start_day_sums_gt1440": int(byday.gt(1440 + 1e-8).sum()), "utc_start_day_sum_max": float(byday.max()),
                  "approximate_interval_overlap_rows": int(overlap.sum()),
                  "approximate_interval_overlap_people": int(chronological.loc[overlap, "pid"].nunique()),
                  "corrected_duration_discrepancy_gt1sec": int(duration_error.gt(1/60 + 1e-8).sum()),
                  "max_duration_discrepancy_minutes": float(duration_error.max()),
                  "legacy_early_start_hour_gt60": int(earlyhour.gt(60 + 1e-8).sum()),
                  "legacy_early_utc_start_day_gt1440": int(earlyday.gt(1440 + 1e-8).sum()),
                  "legacy_end_after_cutoff": int((oldrows.approximate_session_end > oldrows.end).sum()),
                  "legacy_original_end_after_cutoff": int((oldrows.approximate_session_end_original > oldrows.end).sum()),
                  "legacy_record_timestamp_after_cutoff": int((oldrows.timestamp > oldrows.end).sum()),
                  "legacy_start_before_window": int((oldrows.approximate_session_start < oldrows.start).sum())},
        "secondary": {"consecutive_complete_routine_pairs": len(transitions), "people": transitions.pid.nunique(),
                      "pairs_gap_ge14": int(transitions.gap_days.ge(14).sum()),
                      "people_gap_ge14": int(transitions.loc[transitions.gap_days.ge(14), "pid"].nunique()),
                      "strict_steam_pairs": len(rq2), "strict_steam_people": rq2.pid.nunique(), "strict_records": len(rq2rows),
                      "gap_min_days": float(rq2.gap_days.min()), "clean_value_min": float(q.gaming_value_routines.min()),
                      "clean_value_max": float(q.gaming_value_routines.max())},
        "coverage": {"validated_observation_denominator": False,
                     "reason": "Clean Steam file contains positive approximate-play records, not polling/visibility observations. The provider index uses a separate raw account-linking file plus fallback assumptions. Account visibility would not establish active-play observability. No 80% coverage or true-zero-play claims are made."},
        "interpretation": "Starting-hour sums above 60 are allocation diagnostics, not automatically invalid hours: provider collapses scaled hourly pieces back to approximate records. Intervals can overlap and are not exact sessions. No additional outlier clipping is applied. Strict sensitivity requires whole approximate records and source timestamps within the window and allocates their minutes across elapsed days; it cannot reconstruct the original hourly correction. Prior metrics were already seen; this is exploratory, not preregistered."
    }
    quality['steam'].update(approximate_hour_audit(s))
    quality['steam']['strict_study_day_max'] = float(final.max_minutes.max())
    quality['steam']['strict_people_with_study_day_gt1440'] = int(final.max_minutes.gt(1440+1e-6).sum())
    dump("quality_audit.json", quality)
    descriptions = {name: x[["baseline", "target", "weekly_hours", "active_days", "sd_minutes", "max_minutes", "week_change"]].describe().to_dict()
                    for name, x in (("legacy", legacy), ("strict", final), ("secondary", rq2))}
    dump("feature_summary.json", descriptions)
    print(json.dumps({k: quality[k] for k in ("flow", "gdt_change", "secondary")}, indent=2))

if __name__ == "__main__":
    main()
