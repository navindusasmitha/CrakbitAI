from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class Finding:
    rule_id: str
    title: str
    severity: str
    confidence: str
    file: str
    line: int
    description: str
    remediation: str
    evidence: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
