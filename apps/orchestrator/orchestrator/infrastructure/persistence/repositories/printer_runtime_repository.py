from sqlmodel import Session, select

from orchestrator.domain.models import PrinterRuntime


class SqlModelPrinterRuntimeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[PrinterRuntime]:
        return list(self.session.exec(select(PrinterRuntime)).all())

    def get_by_printer_id(self, printer_id: str) -> PrinterRuntime | None:
        return self.session.exec(select(PrinterRuntime).where(PrinterRuntime.printer_id == printer_id)).first()

    def save(self, row: PrinterRuntime) -> PrinterRuntime:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

