from dataclasses import dataclass, field
from .eprocess import Evidence
from .policies import Policy


@dataclass
class Comparison:
    comparison_id: str
    start: int
    reference: tuple
    candidate: tuple
    move: str
    added: int
    removed: int
    shadow: Policy
    evidence: Evidence
    scores: list = field(default_factory=list)

    def append(self, day, y):
        if day != self.start+len(self.scores):
            raise ValueError('Duplicate or nonconsecutive comparison observation')
        self.scores.append(float(y))
        self.evidence.update(y)
