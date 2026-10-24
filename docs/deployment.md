# Automatic publishing to hellokim.me/hymns

Every push or merge to `Sleepycatfuji/Hymns/main` runs the **Validate and publish
hymns** workflow. Pull requests run validation and build review artifacts only;
they never receive the production publishing key. Automatic production publishing
was enabled at the owner's request after PR #1 was merged.

## Production route

`Hymns/main` → validation → complete release artifact →
`skills-github-pages/main:hymns/` → GitHub Pages → `https://hellokim.me/hymns/`.

The custom domain belongs to `Sleepycatfuji/skills-github-pages`, whose Pages source
is `main` at the repository root. `Hymns` has its own different Pages URL at
`https://sleepycatfuji.github.io/Hymns/`; that is not the user-facing destination.
The publisher does not change the portfolio homepage, CNAME, theme, other pages,
or Pages settings. Its git commit is restricted to the `hymns/` folder.

## What happens on an update

1. All Python tests, all 791 frontend rendering checks, and deterministic dataset
   validation must pass. Commit regenerated data/audit when changing source data:
   run `python update_chorales.py` locally first. Mapping/verse changes require
   source evidence and updated regression expectations, not bypassing tests.
2. CI builds `hymns-release-<commit>` containing frontend, hashed JSON dataset,
   manifest and a hosting control marker. The frontend verifies its dataset hash.
3. The publish job verifies that artifact and skips superseded source commits.
4. It checks out `skills-github-pages/main` and syncs only `hymns/`. Old immutable
   datasets remain for already-open pages; the obsolete mutable dataset is removed.
   Publication uses a normal fast-forward push and retries against newer portfolio
   commits rather than overwriting them. Production jobs are serialized.
5. The portfolio's existing GitHub Pages build publishes the commit. The source
   workflow retries read-only live verification for up to ten minutes and succeeds
   only when the public HTML, dataset and manifest match the source commit.

No one needs to copy files or update the portfolio's hymns folder by hand.
Only updates reaching `main` deploy; unfinished work on other branches does not.

## Status and retries

Open [Hymns Actions](https://github.com/Sleepycatfuji/Hymns/actions) and select
**Validate and publish hymns**. A successful publish job includes the live URL and
source commit in its summary. If tests fail, nothing is published. If a sync or
live verification fails, inspect the failed step and the portfolio's Pages run.
The verification failure does not mean the published content was rolled back.

Use **Run workflow → main** to retry the latest validated source. Re-running an
old superseded commit skips publishing it. To roll back content, revert the source
change on `Hymns/main`; the normal pipeline validates and publishes the revert.
To pause publishing, disable this workflow in Actions (which also pauses its
validation), or remove/disable the `publish` job while keeping validation.

## Publishing credential

The portfolio has a dedicated write-enabled deploy key named
`Hymns automatic publishing`. Its private key is stored only as the encrypted
`PORTFOLIO_DEPLOY_KEY` Actions secret in `Sleepycatfuji/Hymns`. It grants repository
access to the portfolio, not account-wide access; the workflow confines its
changes to `hymns/`. It is not available to the pull-request validation job.
Revoke the key in the portfolio's **Settings → Deploy keys**, and remove the source
secret to disable this credential. Rotate both together if replacing it.

## Build a local preview

From a clean checkout with `requirements.txt` installed:

```sh
python build_release.py --output release
python verify_release.py --directory release
```

Use a new output directory if `release` already exists. The bundle contains
`index.html`, `data/hymns.<sha256>.json`, `release.json` (commit and hashes), and
`.nojekyll`. The existing portfolio still uses Jekyll; the marker inside `hymns/`
does not disable its site-wide theme. Live verification checks all runtime files
and the manifest, but does not require the host to serve that control dotfile.
No individual score PDF links are generated.

## Verify the actual live site

From a clean checkout of the main commit being published, run this read-only check
after the workflow completes:

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
