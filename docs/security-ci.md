# Security checks on pull requests

Three workflows run on every pull request. Each one works out what is actually
in the tree before it does anything, so while parts of the repository are still
empty the matching jobs skip and the check goes green rather than red.

Each workflow ends in a single job named after the workflow (`SAST`,
`Terraform`, `DAST`). Those three are the ones to mark as required in branch
protection: they stay stable as jobs come and go underneath them.

## SAST — `.github/workflows/sast.yml`

| Job | Tool | Runs when |
| --- | --- | --- |
| CodeQL | `github/codeql-action` | Python or JS/TS files exist |
| Semgrep | `semgrep` OSS rules | Python or JS/TS files exist |
| Secret scan | `gitleaks` | always |
| Dependency review | `actions/dependency-review-action` | always, on pull requests |

CodeQL runs one matrix leg per language found, with the `security-and-quality`
query suite, and publishes to the Security tab. Semgrep runs `p/default` and
`p/secrets` and fails the build only on `ERROR` severity, so a new finding has
to be high confidence before it blocks a pull request. Gitleaks walks the full
commit history, not just the diff, so a secret committed earlier in a branch is
still caught. Dependency review fails on `high` and above, and runs only once a dependency
manifest exists — it errors out rather than passing quietly when there is
nothing to review. It also needs the repository's **Dependency graph** to be
turned on, under Settings → Code security. Turn it on before the first
`package.json` or `pyproject.toml` lands, or the check will start failing then.

Everything uploads SARIF, so findings land as code scanning alerts and get
annotated inline on the diff. Uploads are skipped for pull requests from forks,
where the token is read-only — the scan still runs and still fails the job.

## Terraform — `.github/workflows/terraform.yml`

There is no Terraform in the repository yet. The `detect` job looks for `*.tf`
files and, finding none, skips every downstream job; the `Terraform` check
passes. When the first `.tf` file lands, these start running on their own:

- `terraform fmt -check -recursive` and, per directory containing `.tf` files,
  `terraform init -backend=false` plus `terraform validate`. The
  `-backend=false` is what keeps this from needing any Cloudflare credentials.
- `tflint --recursive`, failing on `error` severity.
- Trivy config scanning, failing on `HIGH` and `CRITICAL`.
- Checkov across the `terraform` framework.

Trivy and Checkov overlap deliberately — they have different rule sets, and
misconfiguration scanners are cheap to run.

## DAST — `.github/workflows/dast.yml`

Dynamic scanning needs something running, and this repository has no deployment
yet. Rather than block on that, the default target is built inside the job:

**Ephemeral local target.** When a directory with an `index.html` exists (`web`,
`frontend`, `frontend/public`, `public`, `dist`, `site` or the repository root,
or whatever the `DAST_STATIC_DIR` repository variable names), the job serves it
from the runner on `127.0.0.1:8080` and runs a ZAP baseline scan against it.
Nothing outside the runner is touched. A bare `python -m http.server` sends none
of the security headers Cloudflare Pages will send, so header warnings here are
an artifact of the harness rather than a defect in the change — this job fails
on ZAP `FAIL` rules and on scan errors, and only warns on `WARN` rules.

**Deployed target.** Set a `DAST_TARGET_URL` repository variable to a preview or
staging URL, or pass one to a manual run, and a second job scans it. This one
fails on warnings too, because a real deployment is expected to be sending its
headers. It is a *baseline* scan — passive only, never an active attack — so it
is safe to point at a shared environment. Do not point it at production.

Neither job scans the Python Worker API: booting a Worker in CI means `wrangler
dev` pulling the Pyodide runtime, which is slow and flaky. Once the API has a
preview deployment, `DAST_TARGET_URL` is where it goes.

Reports are uploaded as build artifacts (`zap-local-target`,
`zap-deployed-target`) and the summary is written into the job summary.

### Tuning ZAP

`.zap/rules.tsv` overrides individual rules, one per line, tab separated:

```
<rule id>	<WARN|IGNORE|FAIL>	<comment>
```

Rule ids are the numbers in the scan report. Nothing is overridden yet. When a
rule fires on something deliberate, add a line and say why.

## A note on deployment

None of these three workflows deploy anything. The DAST local target is served
from the runner's own loopback and the deployed-target job only scans a URL
that already exists, so no job here needs deployment credentials. Deployment
lives in `.github/workflows/deploy.yml` — see [deploy.md](deploy.md).

Any workflow that *does* deploy must run under the GitHub environment named
`shb`, which holds the deployment variables and secrets. Put `environment: shb`
on the deploying job. Two things to watch for: if that environment carries
protection rules such as required reviewers, a job referencing it pauses until
someone approves — so keep it off fast pull request checks — and its variables
are not visible to a job-level `if:`, which is evaluated before the environment
is resolved.
