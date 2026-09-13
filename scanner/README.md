# Crakbit Scanner

This directory is reserved for the deterministic security-analysis core of Crakbit AI.

## Initial MVP Scope

Planned capabilities:

- Python secure-code rules
- JavaScript/TypeScript secure-code rules
- Secret detection with redaction
- Basic configuration checks
- Normalized findings
- Severity and confidence metadata
- Test fixtures for safe/unsafe examples

## Design Rule

The scanner should produce reproducible evidence independently of the AI explanation layer wherever practical.

## Planned Rule Shape

Each rule should eventually define:

- Rule ID
- Title
- Severity
- Confidence
- Language / file type
- Detection logic
- Description
- Remediation guidance
- Safe example
- Unsafe example
- Tests
- False-positive notes

Implementation work has not yet started in this directory.
