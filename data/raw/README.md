# Raw AMP Source Files

Place exported AMP database CSV files in this folder before running:

```powershell
& ".\.venv\Scripts\python.exe" data_ingestion\build_amp_dataset.py
```

Supported filename prefixes:

- `dbaasp_*.csv`
- `dramp_*.csv`
- `custom_*.csv`

Recommended columns from each source:

- `sequence`
- `target` or `target_organism`
- `mic` or `mic_value`
- `unit`
- `label` or `active_label`

The ingestion script will:

1. normalize column names
2. clean sequences
3. derive peptide features
4. infer labels from `label` or `mic`
5. export:
   - `data/amp_master_dataset.csv`
   - `data/amp_dataset.csv`
