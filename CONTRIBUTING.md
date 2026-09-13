# Contributing to Crakbit AI

Thanks for your interest in Crakbit AI.

Crakbit AI is an early-stage security project focused on AI-assisted cybersecurity, secure coding and blockchain security. Contributions that improve defensive security, documentation, accessibility and developer usability are welcome.

## Before You Start

Please read:

- [`README.md`](README.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`SECURITY.md`](SECURITY.md)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)

## Good First Contributions

Useful early contributions include:

- Documentation improvements
- Secure-coding rules
- Scanner test cases
- False-positive reductions
- Developer-experience improvements
- CLI design suggestions
- Architecture feedback
- Accessibility improvements
- Defensive blockchain-security research
- Examples and tutorials

## Contribution Workflow

1. Fork the repository.
2. Create a focused branch, for example:

   ```bash
   git checkout -b feature/python-rule-pack
   ```

3. Make a small, reviewable change.
4. Add or update tests/documentation where relevant.
5. Do not commit secrets or private data.
6. Open a pull request describing the problem, solution and testing performed.

## Pull Request Expectations

A good pull request should explain:

- What changed
- Why the change is needed
- Security implications, if any
- How the change was tested
- Screenshots or sample output for UI/CLI changes
- Any known limitations

Large architectural changes should be discussed in an issue before implementation.

## Security-Focused Contributions

Crakbit AI prioritizes defensive and authorized security use cases.

Contributions should not add features whose primary purpose is unauthorized access, destructive exploitation, credential theft, malware deployment or evasion.

Security testing code should use controlled targets, fixtures, local environments or public testnets where practical.

## Coding Principles

As implementation grows, contributors should aim for:

- Clear, readable code
- Minimal unnecessary dependencies
- Explicit error handling
- Secure defaults
- Input validation
- Tests for security rules
- Reproducible behavior
- Useful logs without leaking secrets
- Human-readable findings

## Scanner Rule Quality

New security rules should ideally include:

- Rule identifier
- Severity
- Description
- Why the pattern is risky
- Safe example
- Unsafe example
- Remediation guidance
- Test cases
- Notes about possible false positives

## Documentation

Documentation changes are valuable contributions. Please prefer concise explanations, examples and links to authoritative references where appropriate.

## Issues

Use issues for:

- Bugs
- Feature proposals
- Documentation gaps
- Architecture discussions
- Non-sensitive security improvements

Do **not** use public issues for sensitive vulnerabilities. Follow [`SECURITY.md`](SECURITY.md).

## Licensing

By contributing, you agree that your contribution may be distributed under the repository's Apache License 2.0 unless a specific file clearly states otherwise.

## Community Standard

Be respectful, evidence-driven and constructive. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
