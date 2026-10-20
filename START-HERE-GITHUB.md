# Build and upgrade to Radar 0.2.0

This is the real next program revision. GitHub Actions turns these source files into the Windows application using the process you already tested.

## 1. Back up and close your current application

1. Open your existing Radar dashboard and select **Back up my data**. Save that ZIP privately.
2. Select **Exit Radar** or exit using its small control window. Wait for an active refresh to finish first.
3. Leave your existing `%LOCALAPPDATA%\AviationCareerRadar` folder in place. The new application reads and upgrades that same folder. Do not upload it, a résumé, or a backup to GitHub.

## 2. Replace the source in your existing GitHub repository

1. Extract `Aviation-Career-Radar-v0.2.0.zip` using **Extract All** in Windows.
2. Open the extracted folder until you see `app.py`, `Radar.spec`, `VERSION`, `radar`, `tests`, and `.github` alongside one another.
3. Open your `aviation-career-radar` repository on GitHub. On the **Code** page, select **Add file → Upload files**.
4. Drag the **contents of that extracted folder**, including the `radar`, `tests` and `build_tools` folders, onto the upload area. Do not create an extra `radar-v0.2.0` parent folder in the repository. Accept replacement of files with the same paths, then commit the changes.
5. Check that the Code page shows `VERSION` at the repository root, and its contents say `0.2.0`. Check that `radar/domain.py` exists. These checks help catch an accidentally nested upload.

### If Windows/GitHub refuses the `.github` folder

Your repository already has a workflow. Open `.github/workflows/build-windows.yml`, click the pencil to edit, and replace its contents with the same file from this extracted package. Commit. You can open the local file in Notepad. Do not rename `.github` to `github`.

If the workflow did not exist, use **Add file → Create new file** and name it exactly `.github/workflows/build-windows.yml`, including the initial dot and slashes, then paste the contents. GitHub showing the compact path `.github/workflows` on the Code page is normal.

The included workflow uses `actions/checkout@v7`, `actions/setup-python@v7` and `actions/upload-artifact@v7` in both upload steps. It runs only when you request it, tests the application, builds it on Windows, then tests the actual executable before uploading the result.

## 3. Build and download the application

1. Select **Actions → Build Windows application → Run workflow**. Choose the branch you just updated, usually `main`, and confirm **Run workflow**.
2. Open the newest run. Wait for the Windows job to turn green.
3. At the bottom of the run summary, download the artifact named **Aviation-Career-Radar-Windows**. Do not choose GitHub's separate **Code → Download ZIP**, which is source code.
4. Extract the artifact into a **new empty folder**. Keep the full folder together, including `_internal`; moving only the EXE will break it.
5. Double-click `AviationCareerRadar.exe`. A small control window and the browser dashboard should open. Check the sidebar says **Version 0.2.0**.
6. Verify your old notes/listings/profile are present. New databases receive the seed sources; upgrades keep your existing sources and notes. Before migration, Radar copies the old database into the data folder's `backups` subfolder.
7. Once the upgrade works, point your desktop shortcut at this new EXE. Retain the previous application folder and private backup until satisfied. Do not run the old version against the migrated data folder.

Normal use requires no terminal, Python installation or paid ChatGPT account. The local dashboard is served on `127.0.0.1`, not published as a website.

## 4. First checks in the new revision

- Open **Profile & imports**, download or copy the prompt, and use it with your résumé in ChatGPT. Upload the resulting JSON, review every change and approve. Gray qualification labels before that import are expected.
- Pin a listing; verify it appears in **My Opportunities**. Add notes, an interaction and a next step. Unpinning preserves the listing and history.
- Open **Sources & testing → Workspace** for one source. Select **Save & test only this source**, inspect each stage and the preview. This test does not import opportunities. **Import preview records** imports the displayed preview; a full refresh imports all returned records. Mark reviewed only after inspecting actual extraction.
- Open **Market briefings**, create a snapshot, review/copy or export the prompt, paste it into ChatGPT and send it yourself. Bring the response back using paste or a text/Markdown file.

## Troubleshooting

**Build fails:** open the red step and share its error text. A failed packaging test prevents a misleading “successful” download. Build diagnostics may be available as a second artifact. The workflow has not been run in your GitHub account as part of creating this package.

**Old dashboard appears:** exit the old controller, close its tab and open the new EXE. Check the version in the sidebar.

**Source says blocked / page only:** use its Workspace, inspect retrieval/extraction/sample stages, and export the troubleshooting report. This is a source connection issue; rerunning the Windows build will not change a site's access policy or HTML format.

**Application fails to open:** keep the entire extracted folder intact. Logs are in `%LOCALAPPDATA%\AviationCareerRadar\logs`. A different local application using port 8765 may prevent startup. A Windows security warning is possible for an unsigned personal build; review its origin and your security controls before choosing whether to run it.

**Restore:** exit Radar first. Extract your private full backup into a separate folder; it should contain `radar.sqlite3` and `resumes`. Preserve the current data folder before replacing its contents with a backup. A pre-migration `.sqlite3` backup contains the database only; retain the résumé files separately. Never restore into a running app.
