from pathlib import Path
from uuid import UUID

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.process_resume",
    autoretry_for=(),
    max_retries=0,
)
def process_resume_task(self, resume_id: str, storage_dir: str) -> dict[str, str]:
    from app.core.config import get_settings
    from app.core.database import get_session_factory
    from app.services.resume_processing import process_resume_record

    settings = get_settings().model_copy(
        update={"resume_storage_dir": Path(storage_dir)}
    )
    session = get_session_factory()()
    try:
        status = process_resume_record(
            session,
            UUID(resume_id),
            settings=settings,
        )
        return {"resume_id": resume_id, "status": status}
    finally:
        session.close()
