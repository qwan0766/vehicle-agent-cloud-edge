from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class UsageEvent:
    request_id: str
    user_id: str
    user_input: str
    command_type: str
    safety: str
    network: str
    execution_status: str
    output: str
    timestamp: str

    def to_dict(self):
        return asdict(self)


class UsageLogger:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)

    def log(self, event: UsageEvent) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def read_recent(self, limit: int = 5) -> List[UsageEvent]:
        if not self.log_path.exists():
            return []

        rows = self.log_path.read_text(encoding="utf-8").splitlines()
        events = []
        for row in rows[-limit:]:
            payload = json.loads(row)
            events.append(UsageEvent(**payload))
        return events

    def read_all(self) -> List[UsageEvent]:
        if not self.log_path.exists():
            return []

        events = []
        for row in self.log_path.read_text(encoding="utf-8").splitlines():
            if not row.strip():
                continue
            payload = json.loads(row)
            events.append(UsageEvent(**payload))
        return events
