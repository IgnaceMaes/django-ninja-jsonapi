# Limitations & Roadmap

## Current limitations

- This is a strong baseline port, but not yet full feature parity with the original FastAPI package test matrix.
- SQLAlchemy compatibility modules still exist in-tree for migration continuity, while Django ORM is the default runtime path.
- Some advanced JSON:API edge cases (deep relationship workflows and full atomic semantics) need broader integration coverage.

## Roadmap ideas

- Expand integration tests for full CRUD payload validation through Ninja test client.
- Add worked example project under `examples/`.
- Document relationship metadata patterns with end-to-end samples.
- Add CI coverage reporting.
