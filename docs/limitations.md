# Limitations & Roadmap

## Current limitations

- Some advanced JSON:API edge cases (deep relationship workflows and full atomic semantics) need broader integration coverage.
- The current test suite is focused and pragmatic; adding more integration tests across real Django models/endpoints would further harden behavior.

## Roadmap ideas

- Expand integration tests for full CRUD payload validation through Ninja test client.
- Add worked example project under `examples/`.
- Document relationship metadata patterns with end-to-end samples.
- Add CI coverage reporting.
