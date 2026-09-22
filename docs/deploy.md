# Deploying

`.github/workflows/deploy.yml` deploys to Cloudflare on every push to `main`,
and on demand via the workflow's "Run workflow" button, where you can pick
whether to deploy the API, the site, or both.

It runs under the **`shb`** GitHub environment, which holds
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Both deploying jobs declare
`environment: shb`, so those secrets are only readable from the jobs that
actually deploy.

Nothing here touches DNS. The API token has no zone permission on purpose, and
the custom domain is a CNAME managed outside this repository.

## What it deploys

| Job | Deploys | Runs when |
| --- | --- | --- |
| `Deploy API` | D1 migrations, then the Worker | a wrangler config exists |
| `Deploy site` | the static site to Pages | a directory with `index.html` exists |

Neither the API nor the site is on `main` yet, so today the detect job finds
nothing, both jobs skip and the `Deploy` check passes. Each switches itself on
when the thing it deploys lands — there is nothing to remember to turn on.

The site deploys after the API, and only if the API deploy did not fail. The
site calls the API, so if a deploy only half succeeds the API should be the
newer of the two.

Deploys are serialised (`concurrency: deploy-shb`) and a deploy already in
flight is never cancelled.

## Things it works out for itself

- **Where the Worker is** — wherever `wrangler.toml`, `wrangler.json` or
  `wrangler.jsonc` is.
- **The D1 database name** — read out of the wrangler config's
  `[[d1_databases]]`, so renaming the database in one place is enough.
  Override with a `CF_D1_DATABASE` repository variable. If migrations exist but
  no name can be found, the job warns and skips them rather than guessing at a
  database to write to.
- **The site directory** — the first of `web`, `frontend`, `frontend/public`,
  `public`, `dist` or `site` holding an `index.html`. Override with a
  `CF_PAGES_DIRECTORY` repository variable.

The one thing it cannot work out is the **Pages project name**, which defaults
to `summit-basecamp`. If the Pages project is called something else, set a
`CF_PAGES_PROJECT` repository variable.

## Migrations

`wrangler d1 migrations apply --remote` runs against the real database before
the Worker deploys. That is a write to production data on every push to `main`
that carries a new migration, so migrations should be written to be safe to
apply ahead of the code that needs them.

## Renaming the Worker or Pages project

Neither can be renamed in place on Cloudflare -- the name is the identifier
the URL is built from, so changing it (`wrangler.jsonc`'s `name`, or a new
`CF_PAGES_PROJECT`) deploys a *new* Worker or Pages project at a *new*
`*.workers.dev`/`*.pages.dev` hostname, leaving the old one behind, still
serving whatever it last deployed, until it's explicitly deleted.

After a rename lands:

1. This repo's own deploy creates the new Worker automatically on its next
   run (Workers don't need pre-creating); the new Pages project needs one
   run of "Provision Cloudflare resources" (`resource: pages`) first, the
   same way the original project was created.
2. Update the `CF_API_BASE_URL` repository variable
   (`.github/workflows/sync-roster.yml`) to the new Worker's hostname --
   forgetting this doesn't error, it just keeps calling the old Worker.
   Check `CF_PAGES_PROJECT` too, if one is set.
3. Confirm the new Worker (`GET /api/health`) and the new Pages site both
   work.
4. Only then, run `.github/workflows/decommission-cloudflare.yml` by hand
   (once per resource) to delete the old Worker and old Pages project. It
   requires typing the exact old resource name as confirmation and never
   runs on its own -- there is no automatic cleanup, on purpose, since
   deleting either is unrecoverable.
