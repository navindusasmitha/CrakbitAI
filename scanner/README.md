# Crakbit Scanner

**Status: early alpha (`0.1.0a1`)**

This directory contains the first deterministic security-analysis component for Crakbit AI.

The scanner is intentionally small and defensive. It does **not execute target code**. It currently performs line-based static checks and produces normalized findings with severity, confidence, evidence and remediation guidance.

## Current Rules

The initial rule set includes checks for:

- Possible hard-coded credentials with evidence redaction
- Python `subprocess` usage with `shell=True`
- Python `eval()`
- JavaScript/TypeScript `eval()`
- Potentially unsafe `innerHTML` assignment

This is an early proof of architecture, not a production-grade security scanner.

## Supported File Types

Initial extensions:

- `.py`
- `.js`
- `.ts`
- `.jsx`
- `.tsx`
- `.go`
- `.rs`
- `.sol`

Not every language currently has language-specific rules.

## Install for Development

From the repository root:

```bash
cd scanner
python -m venv .venv
```

Activate the environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Then install:

```bash
pip install -e ".[dev]"
```

## Run a Scan

```bash
crak scan <path>
```

Example:

```bash
crak scan ../example-project
```

JSON output:

```bash
crak scan ../example-project --json
```

You can also run the module directly:

```bash
python -m crakbit_scanner.cli scan ../example-project
```

## Run Tests

```bash
pytest -q
```

## Important Limitations

- Findings may contain false positives or false negatives.
- A clean scan does not prove code is secure.
- Current detection is intentionally simple and rule-based.
- No dependency-vulnerability database integration exists yet.
- No AST/data-flow analysis exists yet.
- No dynamic execution/sandboxing exists yet.
- AI remediation is not yet connected to this scanner.

## Design Principle

The scanner should produce reproducible evidence independently of the AI explanation layer wherever practical.

AI should explain or help remediate findings, not silently invent scanner evidence.

## Planned Next Steps

- Expand Python rules
- Expand JavaScript/TypeScript rules
- Add structured configuration checks
- Introduce AST-based analysis where useful
- Improve secret detection and allowlists
- Add a documented finding schema
- Add reporting/export improvements
- Connect findings to the future Crakbit AI explanation layer
