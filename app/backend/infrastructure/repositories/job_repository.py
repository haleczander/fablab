from sqlmodel import Session, select

from app.backend.domain.models import BackendJob


class SqlModelJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_jobs(self) -> list[BackendJob]:
        statement = select(BackendJob).order_by(BackendJob.created_at.desc())
        return list(self.session.exec(statement).all())

    def get_by_job_id(self, job_id: str) -> BackendJob | None:
        statement = select(BackendJob).where(BackendJob.job_id == job_id)
        return self.session.exec(statement).first()

    def get_next_queued_for_printer(self, printer_id: str) -> BackendJob | None:
        statement = (
            select(BackendJob)
            .where(BackendJob.printer_id == printer_id, BackendJob.status == "QUEUED")
            .order_by(BackendJob.created_at.asc())
        )
        return self.session.exec(statement).first()

    def save(self, job: BackendJob) -> BackendJob:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job
