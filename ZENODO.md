# Zenodo release status

Concept DOI: <https://doi.org/10.5281/zenodo.21130295>

- Version 0.2.0 was published on 18 July 2026.
- Version 0.3.0 exact DOI: <https://doi.org/10.5281/zenodo.21524096>

Version 0.3.0 is the sanitized, hermetic release associated with Git tag `v0.3.0` and Zenodo draft 21524096. The draft has been created with metadata, the tarball uploaded, and the exact DOI recorded here. It awaits final review and manual publish.

## Release procedure

1. Build and verify the clean public Git commit and tag candidate.
2. Create a new version from the published 0.2.0 record.
3. Record the reserved exact DOI returned by Zenodo and update active citation metadata.
4. Build the deterministic archive from the exact tagged commit.
5. Extract the archive and run the smoke test, focused release tests, manuscript build, path/content scan, and checksum verification.
6. Replace inherited draft files with the verified 0.3.0 archive and manifest.
7. Verify remote filenames, sizes, checksums, metadata, version, related Git tag, and reserved DOI.
8. Publish once and verify the public record independently.

The release contains code, frozen result records, manifests, figures, and manuscript sources. External Matbench Discovery prediction files are documented by filename, size, and SHA-256 in `DATA_MANIFEST.md` and are not redistributed.
