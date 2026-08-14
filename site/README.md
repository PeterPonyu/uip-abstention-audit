# UIP abstention audit (Eleventy)

Public Pages for oxide-localized UIP–label disagreement and matched-yield
abstention. Authoring lives here under `site/`.

## Local build

```bash
cd site
npm ci
npx @11ty/eleventy --pathprefix=/uip-abstention-audit/
```

Artifact: `site/_site/`. Project URL prefix is `/uip-abstention-audit/`.

## Extracts

`scripts/extract_web_json.py` reads frozen analysis records and writes
`data/*.json` plus `assets/web/*.svg`. Do not hand-edit the numeric
JSON.
