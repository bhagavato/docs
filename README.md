# Bhagavato Docs

Documentation site built on the [OINK](https://oink.pgsty.com) Hugo theme,
created from [`pgsty/oink-starter`](https://github.com/pgsty/oink-starter).

- **Production:** <https://bhagavato-docs.pages.dev/>
- **Languages:** English (default) and Simplified Chinese
- **Theme:** pinned in `go.mod` as a Hugo Module

## Local development

```bash
hugo server                       # preview at http://localhost:1313/
hugo mod graph | grep oink        # confirm the resolved theme version
```

Before pushing, reproduce the CI build exactly:

```bash
hugo --cleanDestinationDir --gc --minify --environment production \
  --printPathWarnings --panicOnWarning
```

`--panicOnWarning` means a warning fails the build. CI runs the same command,
so a clean local run is the precondition for a deploy, not a formality.

## Deployment

A push to `main` builds in GitHub Actions and uploads `public/` to the
Cloudflare Pages project `bhagavato-docs` (Direct Upload).

| Setting | Where | Value |
| --- | --- | --- |
| `CLOUDFLARE_API_TOKEN` | secret | token with Account → Cloudflare Pages → Edit |
| `CLOUDFLARE_ACCOUNT_ID` | secret | Cloudflare account id |
| `CLOUDFLARE_PROJECT_NAME` | variable | `bhagavato-docs` |
| `CLOUDFLARE_PAGES_ENABLED` | variable | `true` |

The Cloudflare project name is deliberately not the repository name: the
`pages.dev` subdomain is globally unique, so `docs.pages.dev` was unavailable.
`CLOUDFLARE_PROJECT_NAME` exists to decouple the two.

`.github/workflows/github-pages.yaml` is kept as a working alternative but is
guarded by `GITHUB_PAGES_ENABLED`, so it never runs alongside the Cloudflare
deploy. Set that variable to `true` to switch hosts.

Never commit `public/`, `resources/`, module caches, or a local module
replacement.
