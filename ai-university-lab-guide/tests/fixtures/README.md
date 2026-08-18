# Test Fixtures

This project intentionally does **not** bundle real photographs of
people, to avoid shipping an unknown/unlicensed image in the
repository.

Most Vision tests use synthetically generated blank frames (NumPy
arrays), which is sufficient to test the "no face" path, invalid-input
handling, and the DetectionResult contract.

Two tests are skipped automatically unless you add real fixture images
locally:

- `tests/fixtures/single_face.jpg` — a photo containing exactly one
  clearly visible human face. Enables `TestSingleFaceFixture`.
- `tests/fixtures/multi_face.jpg` — a photo containing two or more
  clearly visible human faces. Enables `TestMultiFaceFixture`.

These files are covered by `.gitignore`-style exclusion is **not**
applied automatically — if you add real fixture images, make sure you
have the rights to include them before committing.
