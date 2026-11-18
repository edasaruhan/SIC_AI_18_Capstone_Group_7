"""Submitted experiment reproduction and separately versioned final analyses."""
import argparse
import importlib.metadata
import json
import platform
import sys
import warnings
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from .config import ROOT, RESULTS, MODELS, COMMIT, F, prepare_dirs
from .download import sha256

ALPHAS = [.001, .01, .1, 1, 10, 100, 1000]
REFINED = {
    "R_M2": (F[:2], Ridge(), {"reg__alpha": ALPHAS}),
    "R_M3": (F, Ridge(), {"reg__alpha": ALPHAS}),
    "R_EN": (F, ElasticNet(max_iter=20000, tol=1e-5), {"reg__alpha": [.001, .01, .1, 1, 10], "reg__l1_ratio": [.1, .5, .9, 1.]}),
    "R_GB": (F, GradientBoostingRegressor(n_estimators=100, random_state=42), {
        "reg__learning_rate": [.03, .05], "reg__max_depth": [1, 2], "reg__min_samples_leaf": [20, 40]})}
ORIGINAL = {
    **{name: (cols, Ridge(), {"reg__alpha": [.1, 1, 10]}) for name, cols in (("M1", F[:1]), ("M2", F[:2]), ("M3", F))},
    "M3_GB": (F, GradientBoostingRegressor(n_estimators=100, learning_rate=.05, min_samples_leaf=20, random_state=42), {"reg__max_depth": [1, 2]})}
REFERENCES = {
    "M0": [2.1031, 2.8304, .1920], "M1": [1.8846, 2.4057, .4162],
    "M2": [1.8757, 2.3852, .4262], "M3": [1.8778, 2.3893, .4242], "M3_GB": [1.9168, 2.4171, .4107],
    "R_M2": [1.8757, 2.3852, .4262], "R_M3": [1.8778, 2.3893, .4242],
    "R_EN": [1.8837, 2.3892, .4242], "R_GB": [1.9158, 2.4239, .4074], "R_SELECT": [1.9026, 2.4198, .4094]}

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

def metrics(y, pred):
    return {"MAE": float(mean_absolute_error(y, pred)), "RMSE": float(np.sqrt(mean_squared_error(y, pred))), "R2": float(r2_score(y, pred))}

def make_pipeline(estimator):
    return Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("reg", clone(estimator))])

def inner_splits(x, groups=None):
    if groups is None:
        return list(KFold(3, shuffle=True, random_state=43).split(x))
    folds = list(GroupKFold(3).split(x, groups=groups))
    for train, test in folds:
        assert not set(groups[train]) & set(groups[test])
    return folds

def fit_search(candidate, x, y, splits):
    columns, estimator, grid = candidate
    search = GridSearchCV(make_pipeline(estimator), grid, cv=splits,
                          scoring="neg_mean_absolute_error", n_jobs=1, error_score="raise")
    return search.fit(x[columns], y)

def paired_bootstrap(y, p2, p3, groups=None):
    diff = np.abs(y - p3) - np.abs(y - p2)
    rng = np.random.default_rng(42)
    if groups is None:
        boot = [float(rng.choice(diff, len(diff), replace=True).mean()) for _ in range(2000)]
    else:
        # Resample people with all their transitions. Point estimate weights transitions.
        g = pd.DataFrame({"pid": groups, "diff": diff}).groupby("pid").agg(["sum", "count"])["diff"]
        values = g.to_numpy()
        boot = []
        for _ in range(2000):
            draw = values[rng.integers(0, len(values), len(values))]
            boot.append(float(draw[:, 0].sum() / draw[:, 1].sum()))
    return {"difference_MAE": float(diff.mean()), "CI95": np.quantile(boot, [.025, .975]).tolist(),
            "resamples": 2000, "seed": 42, "unit": "person" if groups is None else "person cluster with all transitions",
            "limitation": "Conditional interval from fixed OOF errors; does not refit models or capture training/selection/prior-analysis uncertainty."}

def linear_explanation(pipe, train, test):
    """Exact interventional SHAP for an additive linear model.

    The value function integrates missing features over the empirical training
    marginals. Then phi_j = beta_j * (z_j - E_train z_j). This is not conditional
    SHAP and does not model feature correlations. No evaluation target is used.
    """
    ztrain = pipe[:-1].transform(train)
    ztest = pipe[:-1].transform(test)
    reg = pipe.named_steps["reg"]
    reference = ztrain.mean(axis=0)
    base = float(reg.intercept_ + reference @ reg.coef_)
    values = (ztest - reference) * reg.coef_
    error = float(np.max(np.abs(base + values.sum(axis=1) - pipe.predict(test))))
    assert error < 1e-8
    return np.abs(values).sum(axis=0), error

def evaluate(x, label, original=False, grouped=False, explain=False):
    y = x.target.to_numpy()
    groups = x.pid.to_numpy() if grouped else None
    specs = {**(ORIGINAL if original else {"R_M1": (F[:1], Ridge(), {"reg__alpha": ALPHAS})}), **REFINED}
    predictions = {k: np.empty(len(y)) for k in specs}
    predictions.update({"M0": x.baseline.to_numpy().copy(), "R_SELECT": np.empty(len(y))})
    outer = list(GroupKFold(5).split(x, groups=groups)) if grouped else list(KFold(5, shuffle=True, random_state=42).split(x))
    fold_rows, explanations = [], []
    assignments = np.empty(len(y), dtype=int)
    for number, (train, test) in enumerate(outer, 1):
        print(f"{label}: fold {number}/5, train={len(train)} heldout={len(test)}", flush=True)
        assignments[test] = number
        assert not set(x.pid.iloc[train]) & set(x.pid.iloc[test])
        splits = inner_splits(x.iloc[train], groups[train] if grouped else None)
        fits = {}
        for name, candidate in specs.items():
            search = fit_search(candidate, x.iloc[train], y[train], splits)
            columns = candidate[0]
            predictions[name][test] = search.predict(x.iloc[test][columns])
            fits[name] = search
            fold_rows.append({"fold": number, "model": name, "train_rows": len(train), "heldout_rows": len(test),
                              "heldout_people": int(x.pid.iloc[test].nunique()), "parameters": search.best_params_,
                              "inner_MAE": float(-search.best_score_),
                              "training_MAE": float(mean_absolute_error(y[train], search.predict(x.iloc[train][columns]))),
                              **metrics(y[test], predictions[name][test])})
            if explain and name in ("R_M2", "R_M3"):
                pi = permutation_importance(search.best_estimator_, x.iloc[test][columns], y[test],
                                            scoring="neg_mean_absolute_error", n_repeats=20, random_state=42, n_jobs=1)
                totals, error = linear_explanation(search.best_estimator_, x.iloc[train][columns], x.iloc[test][columns])
                for j, col in enumerate(columns):
                    explanations.append({"fold": number, "model": name, "feature": col, "heldout_rows": len(test),
                                         "permutation_MAE_increase": float(pi.importances_mean[j]),
                                         "permutation_repeat_sd": float(pi.importances_std[j]),
                                         "mean_absolute_SHAP": float(totals[j] / len(test)), "SHAP_max_additivity_error": error})
        winner = max(REFINED, key=lambda k: fits[k].best_score_)
        predictions["R_SELECT"][test] = predictions[winner][test]
        fold_rows.append({"fold": number, "model": "R_SELECT", "selected_family": winner,
                          "heldout_rows": len(test), "heldout_people": int(x.pid.iloc[test].nunique()),
                          "parameters": fits[winner].best_params_, "inner_MAE": float(-fits[winner].best_score_),
                          **metrics(y[test], predictions["R_SELECT"][test])})
    summary = {k: metrics(y, values) for k, values in predictions.items()}
    intervals = {"R_M3_minus_R_M2": paired_bootstrap(y, predictions["R_M2"], predictions["R_M3"], groups)}
    if original:
        intervals["M3_minus_M2"] = paired_bootstrap(y, predictions["M2"], predictions["M3"])
        intervals["R_SELECT_minus_M2"] = paired_bootstrap(y, predictions["M2"], predictions["R_SELECT"])
    result = {"analysis": label, "rows": len(x), "people": int(x.pid.nunique()), "grouped_by_person": grouped,
              "outer": "GroupKFold(5)" if grouped else "KFold(5, shuffle=True, random_state=42)",
              "inner": "GroupKFold(3)" if grouped else "KFold(3, shuffle=True, random_state=43)",
              "metrics": summary, "paired_uncertainty": intervals,
              "validation": "Exploratory internal nested CV. Cohort and previous results already inspected; no external or untouched test set.",
              "target": "next-survey sign-reversed routine interference (-3 to +3)" if grouped else "wave 6 GDT total (4 to 20)",
              "warnings": []}
    if grouped:
        result["person_balanced_MAE"] = {k: float(pd.DataFrame({"pid": groups, "err": np.abs(y - v)}).groupby("pid").err.mean().mean()) for k, v in predictions.items()}
    if original:
        result["reference_comparison"] = {k: {metric: {"reference": ref, "actual": summary[k][metric], "delta": summary[k][metric] - ref,
                                                        "matches_4dp": bool(round(summary[k][metric], 4) == ref)}
                                               for metric, ref in zip(("MAE", "RMSE", "R2"), refs)} for k, refs in REFERENCES.items()}
    write_json(RESULTS / f"{label}.json", result)
    write_json(RESULTS / f"{label}_folds.json", fold_rows)
    if explanations:
        write_json(RESULTS / f"{label}_explanations.json", explanations)
    private = pd.DataFrame({"pid": x.pid, "target": y, "fold": assignments, **predictions})
    private.to_csv(ROOT / f"data/derived/{label}_oof.csv.gz", index=False)
    print(json.dumps(summary, indent=2), flush=True)
    return result

def refit(x, mode):
    y = x.target.to_numpy()
    fits = {k: fit_search(v, x, y, inner_splits(x)) for k, v in REFINED.items()}
    winner = max(fits, key=lambda k: fits[k].best_score_)
    columns = REFINED[winner][0]
    bundle = {"model": fits[winner].best_estimator_, "features": columns, "data_commit": COMMIT,
              "timing_mode": mode, "model_version": f"gdt-{mode}-2", "family": winner}
    path = MODELS / ("legacy_reference.joblib" if mode == "legacy" else "research_model.joblib")
    synthetic = pd.DataFrame([[8, 12, 10, 90, 300, 2]], columns=F)[columns]
    before = float(bundle["model"].predict(synthetic)[0])
    joblib.dump(bundle, path)
    loaded = joblib.load(path)
    after = float(loaded["model"].predict(synthetic)[0])
    assert abs(before - after) < 1e-12
    metadata = {"artifact": path.name, "sha256": sha256(path), "features": columns, "data_commit": COMMIT,
                "timing_mode": mode, "model_version": bundle["model_version"], "family": winner,
                "parameters": fits[winner].best_params_, "training_people": len(x),
                "full_data_inner_MAE": {k: float(-v.best_score_) for k, v in fits.items()},
                "refit_is_not_test": True, "synthetic_8_12": after, "save_load_difference": abs(before - after),
                "legacy_reference_7_3435_difference": after - 7.3435,
                "training_ranges": {c: [float(x[c].min()), float(x[c].max())] for c in columns},
                "versions": {k: importlib.metadata.version(k) for k in ("scikit-learn", "numpy", "pandas", "joblib")}}
    if winner in ("R_M2", "R_M3", "R_EN"):
        pipe = bundle["model"]
        scaler = pipe.named_steps["scale"]
        reg = pipe.named_steps["reg"]
        metadata["linear_model"] = {"scaled_intercept": float(reg.intercept_), "scaled_coefficients": dict(zip(columns, reg.coef_.tolist())),
                                     "means": dict(zip(columns, scaler.mean_.tolist())), "scales": dict(zip(columns, scaler.scale_.tolist())),
                                     "raw_unit_coefficients": dict(zip(columns, (reg.coef_ / scaler.scale_).tolist())),
                                     "raw_unit_intercept": float(reg.intercept_ - (reg.coef_ * scaler.mean_ / scaler.scale_).sum())}
    name = "legacy_manifest.json" if mode == "legacy" else "manifest.json"
    write_json(MODELS / name, metadata)
    if mode == "strict":
        write_json(MODELS / "schema.json", {"ordered_features": columns, "type": "finite numeric", "training_ranges": metadata["training_ranges"],
                                            "public_input": "Three fixed synthetic scenario identifiers only; no arbitrary participant features."})
    return metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["legacy", "strict", "secondary", "all"], default="all")
    args = parser.parse_args()
    prepare_dirs()
    write_json(RESULTS / "runtime.json", {"python": sys.version.split()[0], "platform": platform.platform(),
                                       "run_at_utc": datetime.now(timezone.utc).isoformat(),
                                       "packages": {k: importlib.metadata.version(k) for k in ("scikit-learn", "numpy", "pandas", "joblib")}})
    for mode, file, label in (("legacy", "primary_legacy", "legacy"), ("strict", "primary_strict", "primary_final"), ("secondary", "secondary", "secondary")):
        if args.mode not in (mode, "all"):
            continue
        x = pd.read_csv(ROOT / f"data/derived/{file}.csv.gz")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = evaluate(x, label, original=(mode == "legacy"), grouped=(mode == "secondary"), explain=(mode == "strict"))
        result["warnings"] = sorted({str(w.message) for w in caught})
        write_json(RESULTS / f"{label}.json", result)
        if mode != "secondary":
            metadata = refit(x, mode)
            print(f"{mode} refit: {metadata['family']}, synthetic={metadata['synthetic_8_12']:.8f}", flush=True)

if __name__ == "__main__":
    main()
