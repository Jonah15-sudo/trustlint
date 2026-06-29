# Real TLS Dataset — Not Found

## Directories Searched

- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\` (project root)
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\data\` — does not exist
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\datasets\` — does not exist
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\external\` — does not exist
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\downloads\` — does not exist
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\archive\` — does not exist
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\reports\` — exists but empty (no dataset files)
- `C:\Users\U-TECH\Desktop\projectsSPL\spl_v7_project_with_frontier\spl_v7_project\examples\` — contains `real_tls_sample.jsonl` (5 rows, sample only)
- `C:\Users\U-TECH\Desktop\projectsSPL\` — archive ZIP files only, no dataset inside
- `C:\Users\U-TECH\Desktop\` — no matching files
- `C:\Users\U-TECH\Downloads\Telegram Desktop\` — contains Kimi AI file lists (.csv), not TLS data
- `C:\Users\U-TECH\Downloads\genos\` — separate SPL project (JS), no dataset

## File Patterns Searched

- `*.jsonl` — only `examples/real_tls_sample.jsonl` found (5 rows, sample)
- `*.csv` — none found in project; 2 irrelevant Kimi AI CSVs in Telegram Desktop
- `*.parquet` — none found
- `*.ndjson` — none found
- `*.zip` — all are project archives (FINAL3.zip, etc.), none contain a TLS dataset
- Contents containing `tls_valid`, `tls_expiry_days`, `hsts_present`, `csp_present`, `partial_response`, `bytes_received` — only the 5-row sample fixture matches

## Candidate Files Found and Rejected

| File | Reason Rejected |
|---|---|
| `examples/real_tls_sample.jsonl` | 5 rows only (needs 5000+), sample data not real |
| `experiments/backward_check/*.json` | Session/report files, not datasets |
| `experiments/replication/runs/*/*.json` | Campaign result files, not datasets |
| `sheet_20260520_204950_generated_by_Kimi_AI.csv` | File list, not TLS data |
| `sheet_20260516_220143_generated_by_Kimi_AI.csv` | File list, not TLS data |
| `spl_evolution_log.jsonl` | Evolution log, not TLS data |

## Reason No Valid Real Dataset Is Available

The SPL v7.1 project was built with a data contract (`docs/REAL_TLS_DATA_CONTRACT.md`) and validation pipeline (`scripts/validate_real_tls_data.py`, `experiments/real_data_loader.py`) for a real TLS dataset, but the dataset itself was never provided, generated, or placed in the project tree. All existing validation passes have been run against programmatically generated test data (the test fixtures in `tests/test_real_validation_runner.py` generate 5000 rows in-memory with a scripted label distribution).

## Recommended Next Steps

1. **Export from a TLS monitoring system** (e.g., Cloudflare, Let's Encrypt, Shodan, Censys) in JSONL or CSV format matching the schema in `docs/REAL_TLS_DATA_CONTRACT.md`.
2. **Validate immediately** using `python scripts/validate_real_tls_data.py path/to/dataset.jsonl`.
3. **Run the real data validation** with `python -c "from experiments.real_validation_runner import RealValidationRunner; r = RealValidationRunner(); res = r.run('path/to/dataset.jsonl'); print(res)"`.
4. **Minimum requirements**: 5000+ rows, ≥10% positive labels, all 12 required fields present and non-null.
