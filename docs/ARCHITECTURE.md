# Crakbit AI — Architecture Overview

> Status: Initial design document. Architecture will evolve as the Security MVP is implemented and tested.

## 1. Goals

Crakbit AI is intended to provide defensive security assistance across modern software-development workflows.

The architecture should support:

- Secure-code analysis
- Human-readable vulnerability explanations
- Remediation guidance
- Secret detection
- Dependency/configuration checks
- Smart-contract analysis
- CLI and API access
- Git/CI integrations
- Future IDE integrations

The system should keep deterministic security analysis separate from AI-generated explanations wherever practical so findings can remain reproducible and testable.

## 2. High-Level Architecture

```text
+---------------------------+
| Developer / Researcher    |
+-------------+-------------+
              |
              v
+---------------------------+
| Interfaces                |
| Web | CLI | API | CI      |
+-------------+-------------+
              |
              v
+---------------------------+
| Request / Auth Layer      |
| validation | limits       |
+-------------+-------------+
              |
              v
+---------------------------+
| Orchestration Layer       |
| scan jobs | normalization |
+------+------+-------------+
       |      |
       |      +-----------------------+
       v                              v
+----------------------+     +----------------------+
| Deterministic        |     | AI Explanation       |
| Security Engine      |     | / Remediation Layer  |
|                      |     |                      |
| - static rules       |     | - explain finding    |
| - secret detection   |     | - suggest fixes      |
| - dependency checks  |     | - summarize report   |
| - config checks      |     |                      |
| - Solidity rules     |     |                      |
+----------+-----------+     +----------+-----------+
           |                            |
           +-------------+--------------+
                         v
              +----------------------+
              | Findings / Report    |
              | severity | evidence  |
              | guidance | metadata  |
              +----------------------+
```

## 3. Core Components

### 3.1 Web Application

Responsibilities:

- Accept code/repository inputs using approved workflows
- Display findings and severity
- Show remediation guidance
- Surface scan history where supported
- Explain project status and limitations

Security requirements:

- Strong input validation
- CSRF protection where relevant
- Safe rendering/escaping
- Rate limiting
- No accidental storage of secrets
- Clear retention policy

### 3.2 CLI

Planned command concept:

```bash
crak scan ./project
```

Possible outputs:

- Human-readable terminal report
- JSON
- Future SARIF-compatible export exploration

The CLI should be useful without requiring a graphical interface.

### 3.3 API

Planned responsibilities:

- Submit scans
- Retrieve normalized findings
- Manage authentication
- Enforce quotas/rate limits
- Support future integrations

The API must not expose internal model prompts, secrets or infrastructure credentials.

## 4. Security Engine

The deterministic security engine should own findings that can be validated through explicit rules or analyzers.

Planned modules:

### Static Analysis

- Unsafe coding patterns
- Injection risks
- Insecure cryptographic usage
- Dangerous deserialization patterns
- Missing validation

### Secret Detection

Potential detection for:

- API keys
- Private keys
- Access tokens
- Hard-coded credentials

A finding should avoid re-printing an entire discovered secret in logs or UI.

### Dependency Analysis

Planned capabilities:

- Dependency inventory
- Known-risk indicators
- Unsupported/outdated package warnings
- Lockfile-aware analysis where possible

### Configuration Analysis

Potential checks:

- Debug mode
- Overly broad CORS
- Insecure cookie configuration
- Exposed services
- Weak security headers

### Smart-Contract Analysis

Initial focus:

- Solidity
- Access-control mistakes
- Dangerous external calls
- Reentrancy-related patterns
- Arithmetic/economic assumptions
- Risky upgradeability/privilege patterns

Blockchain-security findings should explain assumptions and avoid presenting heuristic results as certainty.

## 5. AI Explanation Layer

AI should primarily improve understanding and remediation rather than fabricate scanner evidence.

Good uses:

- Explain why a finding matters
- Translate a technical issue into developer-friendly language
- Suggest safer patterns
- Generate remediation examples
- Summarize a report

Required safeguards:

- Clearly separate scanner evidence from model-generated interpretation
- Avoid inventing vulnerabilities that deterministic analysis did not observe without labeling them as hypotheses
- Do not send secrets to external models when avoidable
- Support local/self-hosted model options where practical
- Record model/version metadata for reproducibility where appropriate

## 6. Finding Schema

A normalized finding should eventually contain fields similar to:

```json
{
  "rule_id": "CRAK-PY-001",
  "title": "Hard-coded credential",
  "severity": "high",
  "confidence": "high",
  "file": "app/config.py",
  "line": 18,
  "evidence": "redacted",
  "description": "A credential appears to be embedded in source code.",
  "remediation": "Move the secret to an approved secret-management mechanism."
}
```

## 7. Severity Model

Initial severity classes:

- Critical
- High
- Medium
- Low
- Informational

Severity should consider exploitability, impact, confidence and context rather than relying only on keywords.

## 8. Data Handling

Security tooling may receive sensitive source code. The project should work toward:

- Data minimization
- Explicit retention rules
- Encryption in transit
- Encryption at rest where storage is required
- Redaction of detected secrets
- Clear user controls for deletion
- Local scanning options for sensitive environments

## 9. Isolation

Untrusted code should never be executed directly on production infrastructure without strict sandboxing.

Static analysis should be preferred for the initial MVP. Any future dynamic analysis must use isolated, resource-limited environments designed for hostile inputs.

## 10. Observability

Operational logs should capture enough information to diagnose failures without storing source code, credentials or full secrets unnecessarily.

Planned metrics may include:

- Scan duration
- Rule execution status
- Failure rate
- Finding counts by severity
- False-positive feedback

## 11. Future Blockchain Network

The Crakbit blockchain is a later research track and is not a dependency for the initial Security MVP.

Any testnet architecture should receive its own threat model, consensus analysis and independent security review before production consideration.

## 12. Architecture Principles

1. Defensive utility first
2. Deterministic evidence before AI narrative
3. Secure defaults
4. Least privilege
5. Data minimization
6. Transparent limitations
7. Reproducible findings
8. Open interfaces where practical
9. Human review for high-impact decisions
10. Test before scale
