# summit-hearth-and-bench

Collaborative season ticket allocation, expense splitting ledger, and daily
NWSL player flashcards. Cloudflare stack (Pages, Python Workers, D1, KV).

## Getting started

```sh
npm install
npm run migrate:local
npm run seed:local
npm run dev
npm test
```

Then, with the dev server up:

```sh
curl -H 'X-Dev-User: usr_ada' http://localhost:8787/api/groups
```

See [docs/backend.md](docs/backend.md) for the layout, the endpoint list, the
data model, and what is deliberately left unimplemented.

Static assets (player headshots, club crests) are committed under
`frontend/public/assets/images/` and served by Pages; there is no object
storage bucket in this stack.
