import uuid

from sqlalchemy.orm import Session

from backend.shared.enums import LogLevel
from backend.shared.models import ExecutionLog


def write_log(db: Session, execution_id: uuid.UUID, message: str, level: str = LogLevel.INFO) -> None:
    db.add(ExecutionLog(execution_id=execution_id, message=message, level=level))
    db.commit()
