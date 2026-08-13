# JCP companion (Eleventy)

Static companion for the public host `PeterPonyu/uip-abstention-audit`.
Not a revised manuscript. Science IA follows the portfolio design note
for this paper. Authoring lives here under `site/`, not in the private
nested tree.

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
JSON. Do not copy manuscript PDFs into this tree.
