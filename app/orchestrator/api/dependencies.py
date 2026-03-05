from fastapi import Depends
from sqlmodel import Session

from app.orchestrator.application.app_services import CommandQueueService, FleetViewService
from app.orchestrator.application.use_cases import (
    EnqueueStartPrintCommandUseCase,
    GetBindingByPrinterIdUseCase,
    GetBindingByIpUseCase,
    IngestDeviceStateUseCase,
    ListBindingsUseCase,
    ListDeviceRuntimesUseCase,
    ListFleetUseCase,
    ListPrinterRuntimesUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    MarkJobSentUseCase,
    PopNextCommandUseCase,
    UpsertBindingUseCase,
    UpsertPrinterRuntimeUseCase,
)
from app.orchestrator.domain.services import OrchestratorDomainService
from app.orchestrator.infrastructure.backend_gateway import BackendGateway
from app.orchestrator.infrastructure.db import get_session
from app.orchestrator.infrastructure.repositories import (
    SqlModelDeviceRuntimeRepository,
    SqlModelPrinterBindingRepository,
    SqlModelPrinterRuntimeRepository,
)

_command_queue = CommandQueueService()


def get_backend_gateway() -> BackendGateway:
    return BackendGateway()


def get_domain_service() -> OrchestratorDomainService:
    return OrchestratorDomainService()


def get_binding_repo(session: Session = Depends(get_session)) -> SqlModelPrinterBindingRepository:
    return SqlModelPrinterBindingRepository(session)


def get_printer_runtime_repo(session: Session = Depends(get_session)) -> SqlModelPrinterRuntimeRepository:
    return SqlModelPrinterRuntimeRepository(session)


def get_device_runtime_repo(session: Session = Depends(get_session)) -> SqlModelDeviceRuntimeRepository:
    return SqlModelDeviceRuntimeRepository(session)


def get_fleet_view_service(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    printer_runtime_repo: SqlModelPrinterRuntimeRepository = Depends(get_printer_runtime_repo),
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
) -> FleetViewService:
    return FleetViewService(
        binding_repo=binding_repo,
        printer_runtime_repo=printer_runtime_repo,
        device_runtime_repo=device_runtime_repo,
    )


def get_list_printer_runtimes_use_case(
    printer_runtime_repo: SqlModelPrinterRuntimeRepository = Depends(get_printer_runtime_repo),
) -> ListPrinterRuntimesUseCase:
    return ListPrinterRuntimesUseCase(printer_runtime_repo)


def get_list_device_runtimes_use_case(
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
) -> ListDeviceRuntimesUseCase:
    return ListDeviceRuntimesUseCase(device_runtime_repo)


def get_list_bindings_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> ListBindingsUseCase:
    return ListBindingsUseCase(binding_repo)


def get_list_fleet_use_case(
    fleet_view: FleetViewService = Depends(get_fleet_view_service),
) -> ListFleetUseCase:
    return ListFleetUseCase(fleet_view)


def get_list_unbound_ips_use_case(
    fleet_view: FleetViewService = Depends(get_fleet_view_service),
) -> ListUnboundIpsUseCase:
    return ListUnboundIpsUseCase(fleet_view)


def get_machine_states_payload_use_case(
    fleet_view: FleetViewService = Depends(get_fleet_view_service),
) -> MachineStatesPayloadUseCase:
    return MachineStatesPayloadUseCase(fleet_view)


def get_upsert_binding_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> UpsertBindingUseCase:
    return UpsertBindingUseCase(binding_repo, device_runtime_repo, domain_service)


def get_upsert_printer_runtime_use_case(
    printer_runtime_repo: SqlModelPrinterRuntimeRepository = Depends(get_printer_runtime_repo),
    backend_gateway: BackendGateway = Depends(get_backend_gateway),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> UpsertPrinterRuntimeUseCase:
    return UpsertPrinterRuntimeUseCase(
        printer_runtime_repo=printer_runtime_repo,
        backend_gateway=backend_gateway,
        domain_service=domain_service,
    )


def get_ingest_device_state_use_case(
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    upsert_printer_runtime: UpsertPrinterRuntimeUseCase = Depends(get_upsert_printer_runtime_use_case),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> IngestDeviceStateUseCase:
    return IngestDeviceStateUseCase(device_runtime_repo, binding_repo, upsert_printer_runtime, domain_service)


def get_mark_job_sent_use_case(
    upsert_printer_runtime: UpsertPrinterRuntimeUseCase = Depends(get_upsert_printer_runtime_use_case),
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> MarkJobSentUseCase:
    return MarkJobSentUseCase(upsert_printer_runtime, binding_repo, device_runtime_repo, domain_service)


def get_binding_by_ip_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> GetBindingByIpUseCase:
    return GetBindingByIpUseCase(binding_repo)


def get_binding_by_printer_id_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> GetBindingByPrinterIdUseCase:
    return GetBindingByPrinterIdUseCase(binding_repo)


def get_enqueue_start_command_use_case() -> EnqueueStartPrintCommandUseCase:
    return EnqueueStartPrintCommandUseCase(_command_queue)


def get_pop_next_command_use_case() -> PopNextCommandUseCase:
    return PopNextCommandUseCase(_command_queue)
