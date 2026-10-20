# Verification for revision 0.2.0

This is the implemented feature revision, not the earlier GitHub packaging test.

## Checks completed while preparing this package

- **30 automated tests passed.** Coverage includes legacy-data migration and pre-upgrade backup; idempotent reopen and downgrade refusal; preview/approval/restoration of profiles; stale-import rejection; planned vs earned qualifications; red/green/gray requirement handling and preferred criteria; personal state/history preservation; no-URL leads and listing merge; fixed-site extraction, pagination, details and sample checks; source diagnostics privacy; preview-only tests; briefing snapshot stability; loopback/token protection; and packaging assets.
- JavaScript syntax and Python compile checks passed.
- Offline JavaScript rendering/filter checks exercise all 11 dashboard views, listing/source/profile/briefing dialogs, unknown-state handling, future groups, pinned results and escaping. This uses a DOM stub: it does not certify actual browser layout or every interaction.
- A **Linux frozen build** made with the included PyInstaller spec passed its executable smoke test: resource loading, seed state, résumé archival dependency, local HTTP assets, profile preview/approval, no-URL lead entry, pinned tracking, reviewed green qualification, briefing creation/import and authenticated shutdown.

## Windows verification

A Windows executable cannot be produced or certified by the Linux build. The included GitHub Actions workflow builds on `windows-latest`, runs the tests, then launches the actual Windows EXE with isolated data and checks its resources and revision-2 behavior before uploading it. This workflow still needs to run in your repository. The native controller and real browser appearance should also be checked on your Windows 11 PC.

The earlier packaging-test build worked on your PC; this new source revision must be built again. A green previous run does not verify these new files.

## Site coverage

Source tests here use controlled public-page/feed-shaped fixtures. This package does not certify that all 31 seed connections currently work or extract complete job lists. Historical research and earlier source-health observations remain dated. Use the new workspace to inspect each source and share a focused troubleshooting report when needed.

## Workflow references

The included major action versions exist in the official repositories: [checkout](https://github.com/actions/checkout/releases), [setup-python](https://github.com/actions/setup-python/releases), [upload-artifact](https://github.com/actions/upload-artifact/releases). These are references for build maintenance, not evidence that a build has run in your repository.
