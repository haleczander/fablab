from sqlmodel import Session, select

from app.orchestrator.domain.models import PrinterBinding


class SqlModelPrinterBindingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[PrinterBinding]:
        return list(self.session.exec(select(PrinterBinding)).all())

    def get_by_printer_id(self, printer_id: str) -> PrinterBinding | None:
        return self.session.exec(select(PrinterBinding).where(PrinterBinding.printer_id == printer_id)).first()

    def get_by_ip(self, printer_ip: str) -> PrinterBinding | None:
        return self.session.exec(select(PrinterBinding).where(PrinterBinding.printer_ip == printer_ip)).first()

    def save(self, row: PrinterBinding) -> PrinterBinding:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, row: PrinterBinding) -> None:
        self.session.delete(row)
        self.session.commit()
