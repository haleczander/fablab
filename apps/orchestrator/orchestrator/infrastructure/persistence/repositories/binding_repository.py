from sqlmodel import Session, select

from orchestrator.domain.models import PrinterBinding
from orchestrator.infrastructure.persistence.models import SqlPrinterBinding


class SqlModelPrinterBindingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[PrinterBinding]:
        return [row.to_domain() for row in self.session.exec(select(SqlPrinterBinding)).all()]

    def get_by_id(self, binding_id: int) -> PrinterBinding | None:
        row = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.id == binding_id)).first()
        return row.to_domain() if row else None

    def get_by_printer_id(self, printer_id: str) -> PrinterBinding | None:
        row = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.printer_id == printer_id)).first()
        return row.to_domain() if row else None

    def get_by_ip(self, printer_ip: str) -> PrinterBinding | None:
        row = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.printer_ip == printer_ip)).first()
        return row.to_domain() if row else None

    def get_by_mac(self, printer_mac: str) -> PrinterBinding | None:
        row = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.printer_mac == printer_mac)).first()
        return row.to_domain() if row else None

    def save(self, row: PrinterBinding) -> PrinterBinding:
        existing = None
        if row.id is not None:
            existing = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.id == row.id)).first()
        if existing is None:
            existing = self.session.exec(
                select(SqlPrinterBinding).where(SqlPrinterBinding.printer_mac == row.printer_mac)
            ).first()
        if existing is None and row.printer_id:
            existing = self.session.exec(
                select(SqlPrinterBinding).where(SqlPrinterBinding.printer_id == row.printer_id)
            ).first()

        db_row = existing or SqlPrinterBinding.from_domain(row)
        if existing is not None:
            db_row.update_from_domain(row)

        self.session.add(db_row)
        self.session.commit()
        self.session.refresh(db_row)
        return db_row.to_domain()

    def delete(self, row: PrinterBinding) -> None:
        db_row = None
        if row.id is not None:
            db_row = self.session.exec(select(SqlPrinterBinding).where(SqlPrinterBinding.id == row.id)).first()
        if db_row is None:
            db_row = self.session.exec(
                select(SqlPrinterBinding).where(SqlPrinterBinding.printer_mac == row.printer_mac)
            ).first()
        if db_row is None:
            return
        self.session.delete(db_row)
        self.session.commit()

