# Model card — gdt-strict-2

- Purpose: local fictional research scenarios; later GDT total regression, not diagnosis or screening.
- Training: 543 eligible adult Steam participants, Open Play `eb0a68c1a7ca1fad54e57a1f89b9d5450f8be840`.
- Inputs: ordered baseline, weekly_hours; schema and observed ranges in `schema.json`.
- Timing: baseline + 14 days, complete approximate records and source timestamps; corrected minutes split across elapsed days. Captured minutes do not establish total gameplay or validated observation coverage.
- Algorithm: full-data inner selection among 42 settings chose R_M2, {'reg__alpha': 0.001}. Imputer, scaler and regressor are saved together.
- Internal family-specific nested CV: MAE 1.875689; RMSE 2.385263; R² 0.426136. Entire family-selection procedure MAE: 1.903323. No external test.
- Earlier analysis of this cohort informed design. Do not treat new random splits as untouched tests. Overlapping GDT recall, selection, attrition and incomplete telemetry limit inference.
- Synthetic baseline 8 / recorded weekly hours 12: 7.3436958590; saved/reloaded prediction difference 0.0.
- Exact linear parameters, scales, runtime, digest and source commit: `manifest.json`. SHA-256: `6034c69fcaa62b9791d26baaf271a29c5270bfa577853c8062b46f7a09bf682f`.
- Final raw-unit rule: 2.271042 + 0.596715 × baseline + 0.024911 × recorded hours/week. Coefficients and SHAP are associations within the fitted model, not causal effects.
- Restricted public input: example_a, example_b, example_c. No uploads or arbitrary personal inputs. No clinical categories, treatment recommendations or personal error intervals.
- Joblib loads only the locally trained trusted file after digest/schema/version checks. Replacing both manifest and model defeats a plain checksum; no cryptographic authenticity claim.
- Privacy: the model has learned from research participants; data openness does not make artefacts anonymous or risk-free. Raw/person-level data are omitted from release. No reidentification or linking to external identities.
- Not validated: children, Türkiye, clinical populations, prospective use, complete platform coverage, cloud/HTTPS/multiuser operation. RQ2 is evaluated separately and is not served.
