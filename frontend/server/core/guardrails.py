"""
Prompt-injection defence in depth.

Layer 1 - normalisation: NFKC-fold unicode (defeats homoglyphs), strip zero-width and control
          characters, cap length.
Layer 2 - risk scoring: weighted heuristics produce a score that is LOGGED and attached to the
          message; nothing is silently rewritten, so the model always sees the user's real text.
Layer 3 - structural separation: user text is only ever sent as a `user` turn, company data
          only ever arrives through tool results, and the system prompt states both are untrusted.
Layer 4 - capability control (the real defence): every state-changing tool is authorised against
          the *calling user's* RBAC role, and high-impact actions are routed to the human approval
          queue regardless of what the model asks for. A successful injection can therefore only
          ever produce text or an approval request, never a direct side effect.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060-\u2064\ufeff\u00ad]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# (pattern, weight, label) — weights sum to a 0..1 score, capped.
_SIGNALS = [
    (re.compile(r"ignore\s+(all|any|the|previous|prior|above|earlier)\s+\w*\s*(instructions?|prompts?|rules?|context)", re.I), 0.5, "override_instructions"),
    (re.compile(r"(system|developer)\s+(prompt|message|instructions?)", re.I), 0.3, "system_prompt_reference"),
    (re.compile(r"\byou\s+are\s+(now|no\s+longer)\b", re.I), 0.3, "role_reassignment"),
    (re.compile(r"\b(act|behave|pretend|roleplay)\s+as\s+(an?\s+)?(root|admin|administrator|developer|jailbr\w+|dan)\b", re.I), 0.4, "privilege_roleplay"),
    (re.compile(r"\b(disregard|bypass|disable|turn\s+off)\s+(the\s+)?(safety|security|policy|policies|rules|guardrails?|approval)", re.I), 0.5, "disable_controls"),
    (re.compile(r"<\|[a-z_]+\|>|\[/?(INST|SYS)\]|<<SYS>>|</?(system|assistant|tool_result)>", re.I), 0.4, "control_token"),
    (re.compile(r"\b(reveal|print|show|leak|dump)\s+(your|the)\s+(system|hidden|secret|initial)\s+(prompt|instructions?)", re.I), 0.4, "prompt_exfiltration"),
    (re.compile(r"\b(approve|pay|transfer|delete|fire|terminate)\s+\w+\s+without\s+(approval|review|confirmation)", re.I), 0.5, "skip_human_gate"),
    (re.compile(r"\bbase64\b|\\u00[0-9a-f]{2}|&#x?[0-9a-f]+;", re.I), 0.2, "encoding_obfuscation"),
]

HIGH_RISK_THRESHOLD = 0.6


@dataclass
class Assessment:
    text: str
    score: float
    signals: List[str] = field(default_factory=list)
    truncated: bool = False

    @property
    def high_risk(self) -> bool:
        return self.score >= HIGH_RISK_THRESHOLD

    def as_dict(self) -> dict:
        return {"score": round(self.score, 2), "signals": self.signals, "high_risk": self.high_risk, "truncated": self.truncated}


def normalize(text: str, max_len: int = 4000) -> tuple[str, bool]:
    folded = unicodedata.normalize("NFKC", text or "")
    folded = _ZERO_WIDTH.sub("", folded)
    folded = _CONTROL.sub("", folded)
    folded = re.sub(r"\n{4,}", "\n\n\n", folded).strip()
    truncated = len(folded) > max_len
    return folded[:max_len], truncated


def assess(text: str, max_len: int = 4000) -> Assessment:
    cleaned, truncated = normalize(text, max_len)
    score = 0.0
    signals: List[str] = []
    for pattern, weight, label in _SIGNALS:
        if pattern.search(cleaned):
            score += weight
            signals.append(label)
    return Assessment(text=cleaned, score=min(score, 1.0), signals=signals, truncated=truncated)
