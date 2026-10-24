# Deploy and verify a matching frontend and dataset

**Approval is required before merging or deploying PR #1.** This PR only prepares
and tests the release bundle. No hosting configuration or production files are
changed by the build, verifier, tests or CI workflow.

## Build one release

After approval to merge, use a clean checkout of the exact merged commit (not the
PR's temporary merge ref). Install `requirements.txt`, then run:

```sh
python -m unittest discover -s tests -v
python update_chorales.py --check
node tests/test_frontend.cjs
python build_release.py --output release
python verify_release.py --directory release
```

`release` must be a new directory. Use a different output name if it already
exists. The build fails on tracked uncommitted changes or stale generated data.
CI performs these steps and uploads `hymns-release-<commit>` as an Actions
artifact. The artifact for the successful **main-branch run after merging** is
eligible for deployment; the PR-run artifact is a review preview only.

The bundle contains only:

- `index.html`, with an exact dataset filename and SHA-256 embedded;
- `data/hymns.<sha256>.json`, containing all 791 hymns;
- `release.json`, recording the commit and hashes of all public files;
- `.nojekyll`, for compatible static hosting.

The source checkout continues to load `data/hymns_dataset_updated.json` for local
development. The production bundle uses the hashed filename. Do not manually edit
the bundle or replace its JSON after building it. The frontend verifies the
payload digest before parsing/displaying it and shows a load error if it does
not match. Production must use HTTPS (localhost HTTP also supports previews).

## Publish only after deployment approval

1. Confirm the approved merged commit and successful validation run.
2. Stage the **entire bundle** at the host serving `https://hellokim.me/hymns/`.
   Use that host's atomic release/directory switch so frontend, data and manifest
   become available together. Retain the previous release for rollback.
3. Serve `index.html` and `release.json` with revalidation/no-cache. The hashed
   JSON can be cached as immutable. Purge old HTML/manifest caches if the host
   uses a CDN. Retaining previously hashed data files during rollout also allows
   already-open older pages to continue functioning.
4. Do not copy just the JSON, just the HTML, or the repository root into the
   production folder. A branch-root Pages deployment bypasses the bundle and its
   runtime integrity check. Configure the host to publish the approved artifact
   through its normal approval process instead.
5. Keep deployment disabled on pull-request events. The included CI workflow
   deliberately has no deployment action and only `contents: read` permission.

The repository does not establish how the custom-domain `/hymns/` folder is
published. The live HTML and data previously differed from repository main.
Confirm that hosting destination before publishing; a GitHub Pages deployment
to a different URL is not proof that hellokim.me was updated. No automatic
hosting changes are made here.

## Verify the actual live site

From the clean checkout of the approved merged commit, run this read-only check
**after** deployment:

```sh
python verify_release.py --url https://hellokim.me/hymns/
```

The verifier requests fresh copies of the live manifest, HTML and hashed dataset,
then compares their bytes with a release rebuilt from the checked-out commit.
It rejects a wrong commit, stale HTML, mismatched data, missing files, or a server
returning an HTML fallback in place of JSON. A success message identifies the
commit and confirms all 791 hymns. It does not deploy or repair anything.

For a local bundle preview, serve the bundle directory and verify it:

```sh
python -m http.server 8000 --directory release --bind 127.0.0.1
# In a second terminal, from the clean repository checkout:
python verify_release.py --url http://127.0.0.1:8000/
```

Finally open the actual live URL in a fresh tab, switch to English, and check:

| Hymn | Chorale choices | Separate page reference | Verses |
| --- | --- | --- | --- |
| 5 | 424, 563 | None | 7 |
| 6 | 424, 563 | None | 3 |
| 438 | None | Book page 568 — Nadver C | 1 |
| 440 | 416 | Book page 570 — Agnus Dei | 3 |

Select 563 for hymn 5 or 6, refresh, and check that the preference persists. Check
composer information remains visible. Switch to Danish to check the `Bogside`
label. Page references must never appear as chorale radio-button choices. There
are no individual score PDF links.

If verification fails, do not report the site as updated. Check the destination,
release manifest and caches, or roll back to the previous complete release using
the host's approved deployment process.
