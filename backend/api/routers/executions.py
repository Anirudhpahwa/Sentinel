import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.models import ExecutionLog, JobExecution
from backend.shared.schemas import ExecutionLogRead, JobExecutionRead

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/{execution_id}", response_model=JobExecutionRead)
def get_execution(execution_id: uuid.UUID, db: Session = Depends(get_db)) -> JobExecution:
    execution = db.get(JobExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.get("/{execution_id}/logs", response_model=list[ExecutionLogRead])
def get_execution_logs(execution_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ExecutionLog]:
    execution = db.get(JobExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return list(
        db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.timestamp.asc())
        )
        .scalars()
        .all()
    )
