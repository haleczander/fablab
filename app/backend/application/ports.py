from __future__ import annotations

from typing import Protocol

from app.backend.domain.models import BackendJob, BackendPrinter


class PrinterRepositoryPort(Protocol):
    def list_printers(self) -> list[BackendPrinter]:
        ...

    def get_by_printer_id(self, printer_id: str) -> BackendPrinter | None:
        ...

    def save(self, printer: BackendPrinter) -> BackendPrinter:
        ...


class JobRepositoryPort(Protocol):
    def list_jobs(self) -> list[BackendJob]:
        ...

    def get_by_job_id(self, job_id: str) -> BackendJob | None:
        ...

    def get_next_queued_for_printer(self, printer_id: str) -> BackendJob | None:
        ...

    def save(self, job: BackendJob) -> BackendJob:
        ...
