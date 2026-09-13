# Crakbit AI — Security Model

> Initial threat-model document for the Security MVP. This will evolve as implementation details become concrete.

## Security Objectives

Crakbit AI should protect:

- User source code and scan inputs
- Authentication/session material
- API keys and service credentials
- Scanner integrity
- Findings and reports
- Project infrastructure
- Build/release integrity
- Future blockchain-security research data

## Primary Threats

### Untrusted Input

Source code, archives, configuration files and repository metadata must be treated as untrusted input.

Mitigations:

- Prefer static analysis for the initial MVP
- Validate file types and size limits
- Do not execute submitted code directly
- Reject unsafe archive paths / path traversal
- Apply resource limits
- Redact detected secrets from logs

### Prompt Injection / AI Manipulation

Source code and comments may contain text designed to manipulate an AI model.

Mitigations:

- Treat repository content as data, not trusted instructions
- Keep deterministic scanner findings separate from AI reasoning
- Use structured prompts and explicit trust boundaries
- Do not allow model output to silently override scanner evidence
- Require explicit authorization for any future action-taking capability

### Secret Exposure

Repositories may contain API keys, private keys or credentials.

Mitigations:

- Redact findings by default
- Avoid sending raw secrets to external AI providers
- Do not log complete secrets
- Minimize retention
- Support local analysis for sensitive environments where practical

### Dependency / Supply-Chain Risk

The platform itself may depend on vulnerable packages.

Mitigations:

- Pin/lock dependencies where appropriate
- Review critical dependencies
- Automate dependency alerts when possible
- Keep the dependency footprint small
- Sign/review releases as the project matures

### Authentication and Authorization

Future hosted services may expose user accounts, API keys and project data.

Mitigations:

- Least privilege
- Server-side authorization checks
- Secure session handling
- Rate limiting
- API-key rotation
- Audit-friendly administrative actions

### Denial of Service

Large or malicious inputs may consume excessive resources.

Mitigations:

- Input size limits
- Timeouts
- Concurrency controls
- Scan quotas
- Queue-based processing for expensive work
- Sandboxed workers for future dynamic analysis

## Trust Boundaries

```text
Internet / User
      |
      v
Input Validation + Auth
      |
      v
Orchestration Layer
      |
      +----> Deterministic Scanner
      |
      +----> AI Explanation Layer
      |
      v
Normalized Findings
      |
      v
User-facing Report
```

External AI providers, package registries and blockchain-data providers must be treated as separate trust domains.

## Data Classification

Suggested categories:

- Public project data
- User project metadata
- User source code
- Security findings
- Credentials/secrets
- Operational credentials

Credentials/secrets require the strictest handling and should not be stored unless technically unavoidable.

## Future Dynamic Analysis

Dynamic analysis is explicitly **not** a requirement for the first MVP.

If introduced later, untrusted workloads must run in hardened isolation with:

- Ephemeral workers
- CPU/memory/time limits
- Restricted filesystem
- Restricted network egress
- No production credentials
- Strong tenant separation

## AI Output Safety

AI-generated security guidance may be incorrect. The product should:

- Show confidence/limitations where useful
- Prefer reproducible evidence
- Link findings to actual code locations
- Avoid claiming certainty from weak heuristics
- Encourage human review for high-impact decisions

## Blockchain-Specific Considerations

Smart-contract and blockchain analysis must account for:

- Irreversible transactions
- Privileged roles
- Upgradeability
- Oracle assumptions
- Economic attacks
- Cross-contract interactions
- Chain-specific behavior

A clean static scan does not prove a smart contract is safe.

## Disclosure and Incident Handling

Sensitive vulnerabilities in Crakbit AI should be reported privately according to [`../SECURITY.md`](../SECURITY.md).

A future incident-response process should define:

- Triage ownership
- Severity levels
- Credential rotation
- User notification criteria
- Patch/release process
- Post-incident review

## Security Principle

**Crakbit AI should help users make better security decisions; it should not pretend that automated analysis can guarantee security.**
