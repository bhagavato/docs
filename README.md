# Bhagavato Docs

Documentation site built on the [OINK](https://oink.pgsty.com) Hugo theme,
created from [`pgsty/oink-starter`](https://github.com/pgsty/oink-starter).

- **Production:** <https://docs.arahato.com/>
- **Languages:** Simplified Chinese (default, served at `/`) and English (at `/en/`)
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
| `CLOUDFLARE_SITE_URL` | variable | `https://docs.arahato.com/` |

The Cloudflare project name is deliberately not the repository name: the
`pages.dev` subdomain is globally unique, so `docs.pages.dev` was unavailable.
`CLOUDFLARE_PROJECT_NAME` exists to decouple the two.

`CLOUDFLARE_SITE_URL` overrides the default `https://<project>.pages.dev/` that
the workflow would otherwise derive, and must stay equal to `baseURL` in
`hugo.yaml`. The project still answers on `bhagavato-docs.pages.dev`, but every
absolute URL the build emits points at the custom domain.

`.github/workflows/github-pages.yaml` is kept as a working alternative but is
guarded by `GITHUB_PAGES_ENABLED`, so it never runs alongside the Cloudflare
deploy. Set that variable to `true` to switch hosts.

## Content language convention

Chinese is `defaultContentLanguage`, so **unsuffixed `page.md` is Chinese**;
English is `page.en.md` and French `page.fr.md`.

Changing `defaultContentLanguage` alone is not enough and fails silently: the
unsuffixed files are reassigned to the new default, collide with the explicitly
suffixed peers, and Hugo drops one side without emitting a warning — a strict
`--panicOnWarning` build still passes. Any such change must rename the content
files in the same commit, and the per-language page counts in Hugo's build
table are what proves nothing was lost.

Never commit `public/`, `resources/`, module caches, or a local module
replacement.
