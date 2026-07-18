# Zenodo DOI reservation — exact steps

Status 2026-07-02: **prepared, not run.** No `ZENODO_TOKEN` was available, so no
Zenodo API call has been made. No DOI is reserved yet. `.zenodo.json` (repo root)
is filled in and passes the deposit script's metadata validation (`--dry-run`).

## Prerequisites

1. Create a Zenodo personal access token with scopes `deposit:write` and
   `deposit:actions` at <https://zenodo.org/account/settings/applications>.
2. Export it in the shell that will run the script:

   ```bash
   export ZENODO_TOKEN=<your token>
   ```

3. Make sure the working tree is clean and `HEAD` is the commit you want
   archived (the deposit script archives `HEAD` via `git archive`, not the
   working tree):

   ```bash
   git -C /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research status
   ```

## Steps

All commands use the shared tooling in
`/home/zeyufu/Desktop/ml-reliability-research/reliability-commons/zenodo/`.

1. **Dry run first (no network, always):**

   ```bash
   python3 /home/zeyufu/Desktop/ml-reliability-research/reliability-commons/zenodo/zenodo_deposit.py \
     --repo /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research \
     --dry-run
   ```

   This prints every API call it would make and builds/validates nothing
   remotely. Fix any reported `.zenodo.json` problems before proceeding.

2. **(Optional rehearsal) sandbox deposit** — needs a separate token from
   <https://sandbox.zenodo.org>:

   ```bash
   ZENODO_TOKEN=<sandbox token> python3 \
     /home/zeyufu/Desktop/ml-reliability-research/reliability-commons/zenodo/zenodo_deposit.py \
     --repo /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research \
     --sandbox
   ```

3. **Real draft deposition + DOI prereservation:**

   ```bash
   ZENODO_TOKEN=$ZENODO_TOKEN python3 \
     /home/zeyufu/Desktop/ml-reliability-research/reliability-commons/zenodo/zenodo_deposit.py \
     --repo /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research
   ```

   The script will:
   - build a tarball of `HEAD` (equivalent to the manual command below),
   - create a **draft** deposition with the `.zenodo.json` metadata and a
     prereserved DOI,
   - upload the tarball to the deposition's file bucket,
   - print the reserved DOI and the draft URL.

   **Nothing is published automatically** — publishing remains a manual,
   reviewed step in the Zenodo web UI.

4. **Record the DOI** printed by the script:
   - add it to `README.md` and `CITATION.cff` (`identifiers:` / `doi:` field),
   - cite it in the manuscript's Data & Code Availability section
     (`manuscripts/paper.tex`),
   - commit those edits and push.

## Manual git-archive command (what the script runs internally)

If you need the tarball by hand (e.g., to upload via the Zenodo web UI
instead of the API):

```bash
cd /home/zeyufu/Desktop/ml-reliability-research/materials-mlip-research
git archive --format=tar.gz --prefix=materials-mlip-research/ \
  -o materials-mlip-research-$(git rev-parse --short HEAD).tar.gz HEAD
```

Write the tarball somewhere outside the repo (or delete it afterwards) so it
is not accidentally committed.

## Notes

- License: MIT (see `LICENSE`); `access_right` is `open`. The archived code
  and result JSONs are self-contained; the ~74 MB of external input CSVs
  (Matbench Discovery predictions + WBM summary) are public upstream data and
  are documented with SHA-256 hashes in `DATA_MANIFEST.md`, not bundled.
- Version in `.zenodo.json` is `0.1.0` (pre-submission snapshot). Bump it for
  any re-deposit after manuscript revisions.

## 2026-07-02 — reserved DOI on draft deposition

A draft deposition was created and a DOI reserved, superseding the "prepared,
not run" status at the top of this file. The deposition is **not yet
published/active**: the reserved DOI resolves only after a manual Publish in the
Zenodo web UI.

- Deposition ID: `21130295`
- Reserved DOI: `10.5281/zenodo.21130295`
- Draft URL: <https://zenodo.org/deposit/21130295>
- Archived commit: `5c1144a` (the `git archive` tarball was built at this repo's
  HEAD *before* the DOI-propagation commit).

Note: the uploaded tarball predates the DOI-propagation commit; before pressing
Publish, optionally replace the file in the draft (web UI, or rerun
`zenodo_deposit.py` after deleting the old file) to archive the final state.
