# Security Policy

Crakbit AI is a security-focused project. We welcome responsible reports that help improve the safety of the project, its code and its public infrastructure.

## Supported Scope

During early development, the following are considered in scope when they exist publicly:

- Crakbit AI source code in this repository
- Official Crakbit AI web applications and APIs
- CLI and developer tooling released by this repository
- Authentication and authorization logic
- Data exposure issues
- Dependency-related vulnerabilities
- Smart-contract or blockchain-security components released by the project

Planned or non-existent features are not considered live attack surfaces.

## How to Report a Vulnerability

Please **do not open a public GitHub issue for a sensitive vulnerability**.

Use one of the following private channels when available:

1. GitHub Private Vulnerability Reporting / Security Advisories for this repository.
2. The security contact published on the official Crakbit website: https://crakbit.space

If a private reporting channel is temporarily unavailable, please avoid publishing exploit details until a secure contact method is available.

A useful report should include:

- Affected component
- Vulnerability description
- Reproduction steps
- Proof of concept where safe
- Potential impact
- Suggested remediation, if known

## Responsible Testing Rules

Security research must be conducted safely and in good faith.

Please do not:

- Access, modify or delete data that does not belong to you
- Perform denial-of-service or resource-exhaustion testing
- Use social engineering against users or contributors
- Exfiltrate secrets or personal information
- Pivot into unrelated systems
- Perform destructive exploitation
- Publicly disclose an unresolved vulnerability without reasonable coordination

Use test accounts, local environments, public testnets and other controlled environments whenever possible.

## Response Process

As the project matures, we aim to:

1. Acknowledge valid reports
2. Reproduce and assess the issue
3. Develop and test a fix
4. Publish a security update when appropriate
5. Credit reporters who request public recognition and followed responsible-disclosure practices

Response-time commitments are not yet guaranteed because Crakbit AI is currently an early-stage, founder-led project.

## Security Philosophy

Crakbit AI is being developed primarily for defensive security, secure coding, code review, education and authorized research.

Security features should be designed to help users understand and reduce risk without encouraging unauthorized access or destructive activity.

## Supply-Chain Safety

Contributors should never commit:

- API keys
- Private keys
- Seed phrases
- Passwords
- Production credentials
- Private customer/user data

If a secret is committed accidentally, treat it as compromised and rotate it immediately rather than only deleting it from Git history.

## CRKBIT / Blockchain Notice

CRKBIT is not currently launched and there is no official production token contract. Any contract claiming to represent CRKBIT before an official announcement through the project's verified channels should be treated as unverified.
