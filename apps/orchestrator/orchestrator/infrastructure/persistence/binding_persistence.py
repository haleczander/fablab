from collections.abc import Generator
from contextlib import contextmanager

from orchestrator.application.ports import PrinterBindingPersistencePort
from orchestrator.domain.models import PrinterBinding
from orchestrator.infrastructure.persistence.db import Session, engine
from orchestrator.infrastructure.persistence.repositories.binding_repository import SqlModelPrinterBindingRepository


class SqlModelPrinterBindingPersistenceAdapter(PrinterBindingPersistencePort):
    @contextmanager
    def _repository(self) -> Generator[SqlModelPrinterBindingRepository, None, None]:
        with Session(engine) as session:
            yield SqlModelPrinterBindingRepository(session)

    def list_all(self) -> list[PrinterBinding]:
        with self._repository() as repository:
            return repository.list_all()

    def get_by_id(self, binding_id: int) -> PrinterBinding | None:
        with self._repository() as repository:
            return repository.get_by_id(binding_id)

    def get_by_printer_id(self, printer_id: str) -> PrinterBinding | None:
        with self._repository() as repository:
            return repository.get_by_printer_id(printer_id)

    def get_by_ip(self, printer_ip: str) -> PrinterBinding | None:
        with self._repository() as repository:
            return repository.get_by_ip(printer_ip)

    def get_by_mac(self, printer_mac: str) -> PrinterBinding | None:
        with self._repository() as repository:
            return repository.get_by_mac(printer_mac)

    def save(self, row: PrinterBinding) -> PrinterBinding:
        with self._repository() as repository:
            return repository.save(row)

    def delete(self, row: PrinterBinding) -> None:
        with self._repository() as repository:
            repository.delete(row)
