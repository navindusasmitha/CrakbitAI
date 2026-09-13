from dataclasses import dataclass
import re
from typing import Pattern


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    severity: str
    confidence: str
    description: str
    remediation: str
    pattern: Pattern[str]
    extensions: frozenset[str]
    redact_evidence: bool = False


RULES = (
    Rule(
        rule_id="CRAK-SEC-001",
        title="Possible hard-coded credential",
        severity="high",
        confidence="medium",
        description="A value assigned to a credential-like variable appears to be hard-coded in source code.",
        remediation="Move credentials to an approved secret-management mechanism or environment variable and rotate exposed credentials.",
        pattern=re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\b\s*[:=]\s*[\"'][^\"'\n]{6,}[\"']"),
        extensions=frozenset({".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".sol"}),
        redact_evidence=True,
    ),
    Rule(
        rule_id="CRAK-PY-001",
        title="Python shell command with shell=True",
        severity="high",
        confidence="high",
        description="Using shell=True can create command-injection risk when command content contains untrusted input.",
        remediation="Avoid shell=True where possible and pass arguments as a list. Validate any unavoidable untrusted input.",
        pattern=re.compile(r"\b(subprocess\.(?:run|Popen|call|check_call|check_output))\s*\([^\n]*shell\s*=\s*True"),
        extensions=frozenset({".py"}),
    ),
    Rule(
        rule_id="CRAK-PY-002",
        title="Use of eval()",
        severity="medium",
        confidence="high",
        description="eval() executes dynamically constructed Python expressions and can be dangerous with untrusted input.",
        remediation="Use a safer parser or explicit data handling. Never pass untrusted input to eval().",
        pattern=re.compile(r"(?<![A-Za-z0-9_])eval\s*\("),
        extensions=frozenset({".py"}),
    ),
    Rule(
        rule_id="CRAK-JS-001",
        title="Use of JavaScript eval()",
        severity="medium",
        confidence="high",
        description="eval() executes dynamically constructed JavaScript and can enable code injection when input is not fully trusted.",
        remediation="Replace eval() with explicit parsing or safer APIs and keep untrusted input out of executable code paths.",
        pattern=re.compile(r"(?<![A-Za-z0-9_$])eval\s*\("),
        extensions=frozenset({".js", ".ts", ".jsx", ".tsx"}),
    ),
    Rule(
        rule_id="CRAK-WEB-001",
        title="Potential unsafe innerHTML assignment",
        severity="medium",
        confidence="medium",
        description="Assigning data to innerHTML can create cross-site scripting risk if the value contains untrusted content.",
        remediation="Prefer textContent for plain text or use a trusted sanitizer before inserting HTML.",
        pattern=re.compile(r"\.innerHTML\s*="),
        extensions=frozenset({".js", ".ts", ".jsx", ".tsx"}),
    ),
)
