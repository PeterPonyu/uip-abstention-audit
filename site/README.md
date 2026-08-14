# UIP abstention audit (web)

Static pages for oxide-localized UIP–label disagreement and matched-yield
abstention. Numbers come from the checked-in frozen extracts.

## Local build

```bash
cd site
npm ci
npx @11ty/eleventy --pathprefix=/uip-abstention-audit/
```

Artifact: `site/_site/`. Project URL prefix is `/uip-abstention-audit/`.
