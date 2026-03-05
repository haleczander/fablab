from datetime import datetime, timezone

from sqlmodel import Session, select

from app.backend.client import get_next_job, post_printer_state
from app.config import ORCH_HEARTBEAT_REFRESH_S
from app.orchestrator.domain.models import DeviceRuntime, PrinterBinding, PrinterRuntime
from app.orchestrator.domain.schemas import DeviceIngestInput, PrinterStateInput

ALLOWED_STATUS = {"ON", "OFF", "IN_USE", "ERROR", "IDLE", "PRINTING"}


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _should_refresh_heartbeat(last: datetime, status_changed: bool) -> bool:
    now = datetime.now(timezone.utc)
    elapsed_s = (now - _to_utc(last)).total_seconds()
    return status_changed or elapsed_s >= ORCH_HEARTBEAT_REFRESH_S


def list_bindings(session: Session) -> list[PrinterBinding]:
    return list(session.exec(select(PrinterBinding)).all())


def list_runtimes(session: Session) -> list[PrinterRuntime]:
    return list(session.exec(select(PrinterRuntime)).all())


def list_devices(session: Session) -> list[DeviceRuntime]:
    return list(session.exec(select(DeviceRuntime)).all())


def list_fleet(session: Session) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    bindings = list_bindings(session)
    for b in bindings:
        runtime = session.exec(select(PrinterRuntime).where(PrinterRuntime.printer_id == b.printer_id)).first()
        device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == b.printer_ip)).first()
        heartbeat = None
        if runtime and runtime.last_heartbeat_at:
            heartbeat = runtime.last_heartbeat_at.isoformat()
        elif device and device.last_heartbeat_at:
            heartbeat = device.last_heartbeat_at.isoformat()
        rows.append(
            {
                "printer_id": b.printer_id,
                "printer_ip": b.printer_ip,
                "printer_model": b.printer_model,
                "status": runtime.status if runtime else (device.status if device else None),
                "last_heartbeat_at": heartbeat,
            }
        )
    rows.sort(key=lambda r: r["printer_id"] or "")
    return rows


def list_unbound_ips(session: Session) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    devices = list_devices(session)
    for d in devices:
        if d.is_bound:
            continue
        rows.append(
            {
                "device_ip": d.device_ip,
                "status": d.status,
                "detected_model": d.detected_model,
                "last_heartbeat_at": d.last_heartbeat_at.isoformat() if d.last_heartbeat_at else None,
            }
        )
    rows.sort(key=lambda r: r["device_ip"] or "")
    return rows


def get_binding_by_printer_id(session: Session, printer_id: str) -> PrinterBinding | None:
    return session.exec(select(PrinterBinding).where(PrinterBinding.printer_id == printer_id)).first()


def get_binding_by_ip(session: Session, printer_ip: str) -> PrinterBinding | None:
    return session.exec(select(PrinterBinding).where(PrinterBinding.printer_ip == printer_ip)).first()


def upsert_binding(session: Session, printer_id: str, printer_ip: str, printer_model: str | None = None) -> PrinterBinding:
    by_printer = get_binding_by_printer_id(session, printer_id)
    by_ip = get_binding_by_ip(session, printer_ip)

    device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == printer_ip)).first()
    detected_adapter = device.detected_adapter if device else None
    detected_model = device.detected_model if device else None
    effective_model = printer_model or detected_model

    if by_printer:
        old_ip = by_printer.printer_ip
        if by_ip and by_ip.id != by_printer.id:
            session.delete(by_ip)
            session.commit()

        by_printer.printer_ip = printer_ip
        by_printer.adapter_name = detected_adapter
        by_printer.printer_model = effective_model
        session.add(by_printer)
        session.commit()
        session.refresh(by_printer)
        if old_ip != printer_ip:
            old_device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == old_ip)).first()
            if old_device:
                old_device.is_bound = False
                old_device.bound_printer_id = None
                session.add(old_device)
                session.commit()
        _mark_device_binding(session, device_ip=printer_ip, printer_id=printer_id)
        return by_printer

    if by_ip:
        by_ip.printer_id = printer_id
        by_ip.adapter_name = detected_adapter
        by_ip.printer_model = effective_model
        session.add(by_ip)
        session.commit()
        session.refresh(by_ip)
        _mark_device_binding(session, device_ip=printer_ip, printer_id=printer_id)
        return by_ip

    created = PrinterBinding(
        printer_id=printer_id,
        printer_ip=printer_ip,
        printer_model=effective_model,
        adapter_name=detected_adapter,
    )
    session.add(created)
    session.commit()
    session.refresh(created)
    _mark_device_binding(session, device_ip=printer_ip, printer_id=printer_id)
    return created


def _mark_device_binding(session: Session, device_ip: str, printer_id: str) -> None:
    device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == device_ip)).first()
    if not device:
        return
    device.is_bound = True
    device.bound_printer_id = printer_id
    session.add(device)
    session.commit()


def upsert_runtime(
    session: Session,
    printer_id: str,
    data: PrinterStateInput,
    source_printer_ip: str | None = None,
) -> PrinterRuntime:
    status = data.status if data.status in ALLOWED_STATUS else "OFF"
    row = session.exec(select(PrinterRuntime).where(PrinterRuntime.printer_id == printer_id)).first()

    if not row:
        row = PrinterRuntime(printer_id=printer_id)
        row.last_heartbeat_at = datetime.now(timezone.utc)

    status_changed = row.status != status
    if _should_refresh_heartbeat(row.last_heartbeat_at, status_changed):
        row.last_heartbeat_at = datetime.now(timezone.utc)

    row.status = status
    row.progress_pct = data.progress_pct
    row.nozzle_temp_c = data.nozzle_temp_c
    row.bed_temp_c = data.bed_temp_c
    row.current_job_id = data.current_job_id
    if source_printer_ip is not None:
        row.last_printer_ip = source_printer_ip

    session.add(row)
    session.commit()
    session.refresh(row)

    post_printer_state(
        printer_id,
        {
            "status": row.status,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
            "progress_pct": row.progress_pct,
            "nozzle_temp_c": row.nozzle_temp_c,
            "bed_temp_c": row.bed_temp_c,
            "current_job_id": row.current_job_id,
        },
    )
    return row


def upsert_device_runtime(session: Session, source_ip: str, data: DeviceIngestInput) -> tuple[DeviceRuntime, PrinterRuntime | None]:
    status = data.status if data.status in ALLOWED_STATUS else "OFF"
    device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == source_ip)).first()
    if not device:
        device = DeviceRuntime(device_ip=source_ip)
        device.last_heartbeat_at = datetime.now(timezone.utc)

    status_changed = device.status != status
    if _should_refresh_heartbeat(device.last_heartbeat_at, status_changed):
        device.last_heartbeat_at = datetime.now(timezone.utc)

    binding = get_binding_by_ip(session, source_ip)
    device.is_bound = binding is not None
    device.bound_printer_id = binding.printer_id if binding else None
    device.status = status
    device.progress_pct = data.progress_pct
    device.nozzle_temp_c = data.nozzle_temp_c
    device.bed_temp_c = data.bed_temp_c
    device.current_job_id = data.current_job_id
    device.last_printer_ip = source_ip

    session.add(device)
    session.commit()
    session.refresh(device)

    if not binding:
        return device, None

    printer_state = PrinterStateInput(
        status=status,
        progress_pct=data.progress_pct,
        nozzle_temp_c=data.nozzle_temp_c,
        bed_temp_c=data.bed_temp_c,
        current_job_id=data.current_job_id,
    )
    runtime = upsert_runtime(
        session,
        printer_id=binding.printer_id,
        data=printer_state,
        source_printer_ip=source_ip,
    )
    return device, runtime


def poll_next_job_once(printer_id: str) -> dict[str, str | bool | None]:
    job = get_next_job(printer_id)
    if not job:
        return {"printer_id": printer_id, "job_found": False, "job_id": None}
    return {
        "printer_id": printer_id,
        "job_found": True,
        "job_id": str(job.get("job_id")) if job.get("job_id") is not None else None,
    }


def mark_job_sent_now(session: Session, printer_id: str, job_id: str) -> PrinterRuntime:
    now = datetime.now(timezone.utc)
    row = session.exec(select(PrinterRuntime).where(PrinterRuntime.printer_id == printer_id)).first()
    if not row:
        row = PrinterRuntime(printer_id=printer_id)
    row.status = "IN_USE"
    row.current_job_id = job_id
    row.progress_pct = 0.0
    row.last_heartbeat_at = now
    session.add(row)
    session.commit()
    session.refresh(row)

    binding = get_binding_by_printer_id(session, printer_id)
    if binding:
        device = session.exec(select(DeviceRuntime).where(DeviceRuntime.device_ip == binding.printer_ip)).first()
        if device:
            device.status = "IN_USE"
            device.current_job_id = job_id
            device.progress_pct = 0.0
            device.last_heartbeat_at = now
            session.add(device)
            session.commit()

    post_printer_state(
        printer_id,
        {
            "status": row.status,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
            "progress_pct": row.progress_pct,
            "nozzle_temp_c": row.nozzle_temp_c,
            "bed_temp_c": row.bed_temp_c,
            "current_job_id": row.current_job_id,
        },
    )
    return row
