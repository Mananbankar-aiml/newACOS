# Changelog

## 1.0.0

### Added
- Provider-agnostic (OpenAI-compatible) tool-use agent runtime with 28 typed, RBAC-checked tools; structured `report_outcome` verdicts; automatic model fallback.
- ChatGPT-style agent workspace: persistent conversations, agent picker, tool-call traces, approval links.
- Orchestrator delegation (`delegate_to_agent`) for real inter-agent coordination.
- Persistent agent memory (`remember` / `recall`) backed by MongoDB + BM25.
- Invoice anomaly detection: Isolation Forest, Benford's-law test, robust z-scores; `/api/finance/anomalies`.
- Evaluation harness with synthetic labelled fraud patterns; `/api/ml/evaluate` and `python -m ml.evaluate`.
- Retrieval over uploaded contracts (PDF/TXT/CSV → chunks → BM25) used by the Compliance agent.
- Approval payloads (`proposed_action`) applied only after human approval.
- Google Identity Services sign-in verified server-side.
- GridFS file storage, CI workflow, pytest suite, `.env.example` templates.

### Changed
- Backend split into `core/`, `routers/`, `agents/`, `ml/`, `rag/` packages.
- CORS policy is spec-compliant (no wildcard with credentials).
- Minimum password length raised to 8.

### Fixed
- OTP codes no longer returned by the API by default.
- Idempotent seeding of agents and schedules.
- Blocking network I/O removed from async routes.

### Removed
- Third-party auth gateway, hosted object-storage client, and all scaffolding artefacts.
