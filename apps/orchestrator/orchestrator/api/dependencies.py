from fastapi import Depends
from sqlmodel import Session

from orchestrator.application.app_services import CommandQueueService, FleetViewService
from orchestrator.application.use_cases import (
    CreatePrinterJobUseCase,
    EnqueueStartPrintCommandUseCase,
    GetBindingByMacUseCase,
    GetPrinterMachineInfoUseCase,
    GetBindingByPrinterIdUseCase,
    GetBindingBySerialUseCase,
    GetBindingByIpUseCase,
    IngestDeviceStateUseCase,
    ListBindingsUseCase,
    ListDeviceRuntimesUseCase,
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListPrinterRuntimesUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
    MarkJobSentUseCase,
    PopNextCommandUseCase,
    SyncPrinterStateUseCase,
    UpsertBindingUseCase,
    UpsertPrinterRuntimeUseCase,
)
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.backend_gateway import BackendGateway
from orchestrator.infrastructure.db import get_session
from orchestrator.infrastructure.printer_adapter_registry import PrinterAdapterRegistry
from orchestrator.infrastructure.prusalink_adapter import PrusaLinkAdapter
from orchestrator.infrastructure.repositories import (
    SqlModelDeviceRuntimeRepository,
    SqlModelPrinterBindingRepository,
    SqlModelPrinterRuntimeRepository,
)
from config import (
    ORCH_PRUSALINK_API_KEY,
    ORCH_PRUSALINK_PASSWORD,
    ORCH_PRUSALINK_TIMEOUT_S,
    ORCH_PRUSALINK_USERNAME,
)

_command_queue = CommandQueueService()
_printer_adapters = PrinterAdapterRegistry(
    {
        "prusalink": PrusaLinkAdapter(
            timeout_s=ORCH_PRUSALINK_TIMEOUT_S,
            username=ORCH_PRUSALINK_USERNAME or None,
            password=ORCH_PRUSALINK_PASSWORD or None,
            api_key=ORCH_PRUSALINK_API_KEY or None,
        )
    }
)


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


def get_list_device_binding_rows_use_case(
    device_runtime_repo: SqlModelDeviceRuntimeRepository = Depends(get_device_runtime_repo),
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> ListDeviceBindingRowsUseCase:
    return ListDeviceBindingRowsUseCase(device_runtime_repo=device_runtime_repo, binding_repo=binding_repo)


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


def get_list_unmatched_contract_devices_use_case(
    fleet_view: FleetViewService = Depends(get_fleet_view_service),
) -> ListUnmatchedContractDevicesUseCase:
    return ListUnmatchedContractDevicesUseCase(fleet_view)


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


def get_binding_by_mac_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> GetBindingByMacUseCase:
    return GetBindingByMacUseCase(binding_repo)


def get_binding_by_printer_id_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> GetBindingByPrinterIdUseCase:
    return GetBindingByPrinterIdUseCase(binding_repo)


def get_binding_by_serial_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
) -> GetBindingBySerialUseCase:
    return GetBindingBySerialUseCase(binding_repo)


def get_enqueue_start_command_use_case() -> EnqueueStartPrintCommandUseCase:
    return EnqueueStartPrintCommandUseCase(_command_queue)


def get_pop_next_command_use_case() -> PopNextCommandUseCase:
    return PopNextCommandUseCase(_command_queue)


def get_printer_adapter_registry() -> PrinterAdapterRegistry:
    return _printer_adapters


def get_create_printer_job_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
) -> CreatePrinterJobUseCase:
    return CreatePrinterJobUseCase(binding_repo=binding_repo, adapter_resolver=adapter_registry)


def get_printer_machine_info_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
) -> GetPrinterMachineInfoUseCase:
    return GetPrinterMachineInfoUseCase(binding_repo=binding_repo, adapter_resolver=adapter_registry)


def get_sync_printer_state_use_case(
    binding_repo: SqlModelPrinterBindingRepository = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
    upsert_printer_runtime: UpsertPrinterRuntimeUseCase = Depends(get_upsert_printer_runtime_use_case),
) -> SyncPrinterStateUseCase:
    return SyncPrinterStateUseCase(
        binding_repo=binding_repo,
        adapter_resolver=adapter_registry,
        upsert_printer_runtime=upsert_printer_runtime,
    )

