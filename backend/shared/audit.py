from sqlalchemy.orm import Session

from backend.shared.models import AdminAction


def record_admin_action(
    db: Session, action: str, target_type: str, target_id: str | None = None, detail: str | None = None
) -> None:
    db.add(AdminAction(action=action, target_type=target_type, target_id=target_id, detail=detail))
    db.commit()
