from sqlmodel import Session, select

from backend.domain.models import BackendPrinter


class SqlModelPrinterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_printers(self) -> list[BackendPrinter]:
        statement = select(BackendPrinter).order_by(BackendPrinter.printer_id)
        return list(self.session.exec(statement).all())

    def get_by_printer_id(self, printer_id: str) -> BackendPrinter | None:
        statement = select(BackendPrinter).where(BackendPrinter.printer_id == printer_id)
        return self.session.exec(statement).first()

    def save(self, printer: BackendPrinter) -> BackendPrinter:
        self.session.add(printer)
        self.session.commit()
        self.session.refresh(printer)
        return printer

