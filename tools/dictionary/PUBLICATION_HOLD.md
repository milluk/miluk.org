# Dictionary publication hold

The `dictionary/` tree is intentionally excluded from the public GitHub Pages deployment. The repository files, data, generators, provenance, and restoration materials remain preserved.

This publication hold remains in place pending source-integrity review. Removing the hold or republishing the dictionary requires Troy's explicit authorization.

PR #1 must incorporate this hold before merge and demonstrate that the GitHub Pages artifact still excludes `/dictionary/`.

## Local browser QA (not publication)

The root `_config.yml` exclusion applies only to the Jekyll-built GitHub Pages artifact. It does not remove or disable the checked-out `dictionary/` files. From any exact draft-head checkout, serve the repository directly on the loopback interface:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8000/dictionary/` in a browser. Check the search page, a representative entry, a representative story, and the JSON data routes. Stop the server with `Ctrl-C` when QA is complete.

To inspect a PR head without changing another working tree, an optional disposable worktree can be prepared from the repository clone (replace `PR_NUMBER`):

```sh
miluk_pr_number=PR_NUMBER
git fetch origin "pull/${miluk_pr_number}/head"
git worktree add --detach "../miluk-pr-${miluk_pr_number}-qa" FETCH_HEAD
cd "../miluk-pr-${miluk_pr_number}-qa"
python3 -m http.server 8000 --bind 127.0.0.1
```

This route is localhost-only static-file QA, not a deployed or password-protected preview. Do not bind the server to a public interface.
