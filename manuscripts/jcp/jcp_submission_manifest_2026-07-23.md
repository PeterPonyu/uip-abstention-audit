# JCP submission manifest — 23 July 2026

Target: The Journal of Chemical Physics, fresh initial submission, Article.

## Upload map

- `paper_jcp.pdf`: main manuscript PDF (33 pages).
- `cover_letter.pdf`: cover letter (1 page); `cover_letter.txt` is its plain-text equivalent.
- `jcp_submission_latex_2026-07-23.zip`: independently compilable source attachment.
- No supplementary-information PDF is required: the full sensitivity grid is in the public reproduction archive.

## Artifacts

| file | bytes | SHA-256 |
|---|---:|---|
| `paper_jcp.pdf` | 456329 | `3362629d09dd2ddf8e8d54ae0717c939d753df378fcd3dbcb2871e33e0525dd2` |
| `paper_jcp.tex` | 79917 | `caed3196ec1aefb8698b0ff62e3254c9b980f02a18881483cce7643d3c3a5dca` |
| `paper_jcp.bbl` | 35849 | `2bf5c555bb0e93c237b956112b2389fd91015b18813acefb7b0657ae1129c143` |
| `cover_letter.pdf` | 19651 | `cbf862ba596ab78f03a334cf3d003fed834716bafb0606a7de27ab965ff3b239` |
| `cover_letter.txt` | 2447 | `0016b9a1798aa36190dcea67b2b6346fa2ca541348a86d3ed08a47a383e37dde` |
| `jcp_submission_latex_2026-07-23.zip` | 287001 | `7648765d7fde03fe0d33667efa82f057c3363b881c7f1a86edcea36a6414ad86` |
| `jcp_submission_latex_2026-07-23.sha256` | 102 | `f2ba2c35b04f107dd0bb20bac539812a2f0ddd92377fe750ba96e1ad465009b6` |

## Build and verification

```bash
latexmk -cd -pdf -interaction=nonstopmode -halt-on-error manuscripts/jcp/paper_jcp.tex
python3 manuscripts/jcp/build_submission_package.py
```

The source package is flat-rooted, uses an explicit member allowlist, contains internal `SHA256SUMS`, and has the adjacent external sidecar listed above. It excludes working notes, reviewer instructions, prior-venue material, backups, archives, local paths, and build logs. The PDF and extracted source package were built independently.

Public code: https://github.com/PeterPonyu/uip-abstention-audit
Concept DOI: https://doi.org/10.5281/zenodo.21130295

AI-use declaration: Claude Code (Anthropic, version 2.1.218) was used solely for language editing and manuscript preparation; all output was reviewed and edited by the author.
