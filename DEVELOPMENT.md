# Development and iteration

Python standard-library local backend, SQLite persistence and plain HTML/CSS/JavaScript dashboard. Optional pypdf is bundled for résumé archival text extraction. There are no AI SDKs, API secrets or account connectors.

## Files

| File | Responsibility |
| --- | --- |
| `app.py` | Loopback HTTP routes, local-origin/token protection, launcher entry |
| `radar/domain.py` | Sections, migration normalization, profile schema and transparent comparisons |
| `radar/engine.py` | Refresh/upsert, personal tracking, profile import approval, briefing snapshots |
| `radar/collectors.py` | Public access checks, safe retrieval, per-source rules and diagnostics |
| `radar/extract.py` | HTML, structured JobPosting and job-link parsing |
| `radar/storage.py` | SQLite schema v2, backup and transactional upgrades |
| `radar/runtime.py` | Native controller, instance handling and logs |
| `radar/static/` | Dashboard controls and presentation |
| `radar/seed.json` | Initial dated research, used for fresh installations only |
| `tests/` | Regression tests, source fixtures, data migration and HTTP protection |
| `build_tools/` | Packaged-executable smoke test and offline JavaScript render check |
| `Radar.spec` | PyInstaller one-folder packaging recipe |

Run from source with Python 3.10+: `python app.py`. For an isolated development database, set `AVIATION_RADAR_DATA` to a separate folder. Do not develop against your real saved data. The default app port is 8765; use `--port` to change it.

Verification:

```
python -m unittest discover -s tests -v
python -m compileall -q app.py window_app.py radar build_tools
node --check radar/static/app.js
```

Build dependencies are pinned in `requirements-build.txt`; build with `python -m PyInstaller --clean --noconfirm Radar.spec`. **Windows EXEs must be built on Windows**, as the included Actions workflow does. `build_tools/smoke_executable.py` launches the real frozen binary with isolated data, checks bundled resources/state and performs authenticated shutdown.

## Adding a site

Start in the Source workspace with a public URL, expected sample job URL and preview. Try plain-text URL/title rules, extra URLs and bounded pagination first. Export diagnostics if extraction fails. A custom API/JavaScript site may need a dedicated collector in Python; do not label it verified merely because HTML was downloaded. Tests should use saved minimal fixtures rather than live sites or credentials. Keep access failures separate from zero matching jobs. Never close old listings simply because a connection fails or a listing disappears from one page.

`collect(source)` returns jobs, preview, coverage, digest, current watched-page excerpt, and staged diagnostics. Feed record parsing should preserve original URLs and published text. Collector results never overwrite personal state. Limit requests/timeouts; do not bypass site access restrictions.

## Data upgrades

SQLite `user_version` is 2. Migrate via `Store` and keep the pre-change backup. Database versions newer than this release are rejected to prevent a downgrade. Add a schema migration and preservation tests for future structural changes. Existing installs retain their own source/employer/program records; editing seed.json does not overwrite them.

Approved profile schema is separately versioned as 1 with `kind: aviation_profile`. Unknown facts are null. Only `qualification_profile` approved through the import process is used for matching. Ordinary preference edits and résumé uploads cannot establish earned qualifications. Planned certificates are separate. Do not infer ATP/R-ATP eligibility from a total-hours number.

Keep factual fields, user tracking, source verification and imported AI commentary separate. Qualification is never an opportunity visibility filter. No secrets, private data folders or personal backup ZIPs belong in GitHub.
