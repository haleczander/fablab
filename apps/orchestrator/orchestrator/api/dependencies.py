from collections.abc import Callable
from typing import Any, TypeVar, cast

from fastapi import Depends
from sqlmodel import Session

from orchestrator.api.services.orchestrator_notifier import OrchestratorNotifier
from orchestrator.application.app_services import CommandQueueService, FleetViewService
from orchestrator.application.ports import (
    DeviceRuntimeRepositoryPort,
    DiscoverySnapshotPort,
    PrinterBindingRepositoryPort,
    PrinterRuntimeRepositoryPort,
)
from orchestrator.application.use_cases import (
    CreatePrinterJobUseCase,
    DiscoverNetworkHostsUseCase,
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
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
    PopNextCommandUseCase,
    RefreshNetworkDiscoveryUseCase,
    SetDeviceIgnoredByMacUseCase,
    SetDeviceIgnoredUseCase,
    SyncPrinterStateUseCase,
    UnbindPrinterUseCase,
    UpsertBindingUseCase,
    UpsertPrinterRuntimeUseCase,
)
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.backend.gateway import BackendGateway
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.cache import build_rows_from_discovery
from orchestrator.infrastructure.network_discovery.device_probers import HttpDeviceProber
from orchestrator.infrastructure.network_discovery.snapshot_store import InMemoryDiscoverySnapshotStore
from orchestrator.infrastructure.persistence.db import get_session
from orchestrator.infrastructure.persistence.repositories import (
    SqlModelDeviceRuntimeRepository,
    SqlModelPrinterBindingRepository,
    SqlModelPrinterRuntimeRepository,
)
from orchestrator.infrastructure.printers.adapter_registry import PrinterAdapterRegistry
from orchestrator.infrastructure.printers.prusalink_adapter import PrusaLinkAdapter
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
_device_prober = HttpDeviceProber()
_discovery_snapshot = InMemoryDiscoverySnapshotStore()
_arp_scanner = ScapyArpNeighborScanner()
T = TypeVar("T")


def get_backend_gateway() -> BackendGateway:
    return BackendGateway()


def get_domain_service() -> OrchestratorDomainService:
    return OrchestratorDomainService()


def get_binding_repo(session: Session = Depends(get_session)) -> PrinterBindingRepositoryPort:
    return SqlModelPrinterBindingRepository(session)


def get_printer_runtime_repo(session: Session = Depends(get_session)) -> PrinterRuntimeRepositoryPort:
    return SqlModelPrinterRuntimeRepository(session)


def get_device_runtime_repo(session: Session = Depends(get_session)) -> DeviceRuntimeRepositoryPort:
    return SqlModelDeviceRuntimeRepository(session)


def get_fleet_view_service(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    printer_runtime_repo: PrinterRuntimeRepositoryPort = Depends(get_printer_runtime_repo),
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
) -> FleetViewService:
    return FleetViewService(
        binding_repo=binding_repo,
        printer_runtime_repo=printer_runtime_repo,
        device_runtime_repo=device_runtime_repo,
    )


def get_list_device_runtimes_use_case(
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
) -> ListDeviceRuntimesUseCase:
    return ListDeviceRuntimesUseCase(device_runtime_repo)


def get_list_device_binding_rows_use_case(
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> ListDeviceBindingRowsUseCase:
    return ListDeviceBindingRowsUseCase(
        device_runtime_repo=device_runtime_repo,
        binding_repo=binding_repo,
        discovery_snapshot_provider=_discovery_snapshot.list_rows,
    )


def get_list_bindings_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
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


def get_orchestrator_notifier(
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> OrchestratorNotifier:
    return OrchestratorNotifier(
        list_fleet_use_case=list_fleet_use_case,
        list_unbound_ips_use_case=list_unbound_ips_use_case,
        list_unmatched_contract_devices_use_case=list_unmatched_contract_devices_use_case,
        list_device_binding_rows_use_case=list_device_binding_rows_use_case,
        machine_states_use_case=machine_states_use_case,
    )


def get_upsert_binding_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> UpsertBindingUseCase:
    return UpsertBindingUseCase(binding_repo, device_runtime_repo, domain_service)


def get_upsert_printer_runtime_use_case(
    printer_runtime_repo: PrinterRuntimeRepositoryPort = Depends(get_printer_runtime_repo),
    backend_gateway: BackendGateway = Depends(get_backend_gateway),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> UpsertPrinterRuntimeUseCase:
    return UpsertPrinterRuntimeUseCase(
        printer_runtime_repo=printer_runtime_repo,
        backend_gateway=backend_gateway,
        domain_service=domain_service,
    )


def get_ingest_device_state_use_case(
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    upsert_printer_runtime: UpsertPrinterRuntimeUseCase = Depends(get_upsert_printer_runtime_use_case),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> IngestDeviceStateUseCase:
    return IngestDeviceStateUseCase(device_runtime_repo, binding_repo, upsert_printer_runtime, domain_service)


def get_binding_by_ip_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> GetBindingByIpUseCase:
    return GetBindingByIpUseCase(binding_repo)


def get_binding_by_mac_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> GetBindingByMacUseCase:
    return GetBindingByMacUseCase(binding_repo)


def get_binding_by_printer_id_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> GetBindingByPrinterIdUseCase:
    return GetBindingByPrinterIdUseCase(binding_repo)


def get_binding_by_serial_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> GetBindingBySerialUseCase:
    return GetBindingBySerialUseCase(binding_repo)


def get_enqueue_start_command_use_case() -> EnqueueStartPrintCommandUseCase:
    return EnqueueStartPrintCommandUseCase(_command_queue)


def get_pop_next_command_use_case() -> PopNextCommandUseCase:
    return PopNextCommandUseCase(_command_queue)


def get_printer_adapter_registry() -> PrinterAdapterRegistry:
    return _printer_adapters


def get_create_printer_job_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
) -> CreatePrinterJobUseCase:
    return CreatePrinterJobUseCase(binding_repo=binding_repo, adapter_resolver=adapter_registry)


def get_printer_machine_info_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
) -> GetPrinterMachineInfoUseCase:
    return GetPrinterMachineInfoUseCase(binding_repo=binding_repo, adapter_resolver=adapter_registry)


def get_sync_printer_state_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
    upsert_printer_runtime: UpsertPrinterRuntimeUseCase = Depends(get_upsert_printer_runtime_use_case),
) -> SyncPrinterStateUseCase:
    return SyncPrinterStateUseCase(
        binding_repo=binding_repo,
        adapter_resolver=adapter_registry,
        upsert_printer_runtime=upsert_printer_runtime,
    )


def get_set_device_ignored_use_case(
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
) -> SetDeviceIgnoredUseCase:
    return SetDeviceIgnoredUseCase(device_runtime_repo=device_runtime_repo)


def get_set_device_ignored_by_mac_use_case(
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
) -> SetDeviceIgnoredByMacUseCase:
    return SetDeviceIgnoredByMacUseCase(device_runtime_repo=device_runtime_repo)


def get_unbind_printer_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    device_runtime_repo: DeviceRuntimeRepositoryPort = Depends(get_device_runtime_repo),
) -> UnbindPrinterUseCase:
    return UnbindPrinterUseCase(binding_repo=binding_repo, device_runtime_repo=device_runtime_repo)


def get_discover_network_hosts_use_case() -> DiscoverNetworkHostsUseCase:
    return DiscoverNetworkHostsUseCase(arp_scanner=_arp_scanner, device_prober=_device_prober)


def get_discovery_snapshot() -> DiscoverySnapshotPort:
    return _discovery_snapshot


def get_refresh_network_discovery_use_case(
    discover_network_hosts: DiscoverNetworkHostsUseCase = Depends(get_discover_network_hosts_use_case),
    discovery_snapshot: DiscoverySnapshotPort = Depends(get_discovery_snapshot),
) -> RefreshNetworkDiscoveryUseCase:
    return RefreshNetworkDiscoveryUseCase(
        discover_network_hosts=discover_network_hosts,
        discovery_snapshot=discovery_snapshot,
        discovery_rows_builder=build_rows_from_discovery,
    )


def get(interface: type[T], session: Session | None = None) -> T:
    if interface is PrinterBindingRepositoryPort:
        if not session:
            raise ValueError("Session requise pour PrinterBindingRepositoryPort")
        return cast(T, SqlModelPrinterBindingRepository(session))
    if interface is PrinterRuntimeRepositoryPort:
        if not session:
            raise ValueError("Session requise pour PrinterRuntimeRepositoryPort")
        return cast(T, SqlModelPrinterRuntimeRepository(session))
    if interface is DeviceRuntimeRepositoryPort:
        if not session:
            raise ValueError("Session requise pour DeviceRuntimeRepositoryPort")
        return cast(T, SqlModelDeviceRuntimeRepository(session))
    if interface is FleetViewService:
        return cast(
            T,
            FleetViewService(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                printer_runtime_repo=get(PrinterRuntimeRepositoryPort, session=session),
                device_runtime_repo=get(DeviceRuntimeRepositoryPort, session=session),
            ),
        )
    if interface is ListDeviceRuntimesUseCase:
        return cast(T, ListDeviceRuntimesUseCase(get(DeviceRuntimeRepositoryPort, session=session)))
    if interface is ListDeviceBindingRowsUseCase:
        return cast(
            T,
            ListDeviceBindingRowsUseCase(
                device_runtime_repo=get(DeviceRuntimeRepositoryPort, session=session),
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                discovery_snapshot_provider=_discovery_snapshot.list_rows,
            ),
        )
    if interface is ListFleetUseCase:
        return cast(T, ListFleetUseCase(get(FleetViewService, session=session)))
    if interface is ListUnboundIpsUseCase:
        return cast(T, ListUnboundIpsUseCase(get(FleetViewService, session=session)))
    if interface is ListUnmatchedContractDevicesUseCase:
        return cast(T, ListUnmatchedContractDevicesUseCase(get(FleetViewService, session=session)))
    if interface is MachineStatesPayloadUseCase:
        return cast(T, MachineStatesPayloadUseCase(get(FleetViewService, session=session)))
    if interface is UpsertBindingUseCase:
        return cast(
            T,
            UpsertBindingUseCase(
                get(PrinterBindingRepositoryPort, session=session),
                get(DeviceRuntimeRepositoryPort, session=session),
                get_domain_service(),
            ),
        )
    if interface is UpsertPrinterRuntimeUseCase:
        return cast(
            T,
            UpsertPrinterRuntimeUseCase(
                printer_runtime_repo=get(PrinterRuntimeRepositoryPort, session=session),
                backend_gateway=get_backend_gateway(),
                domain_service=get_domain_service(),
            ),
        )
    if interface is IngestDeviceStateUseCase:
        return cast(
            T,
            IngestDeviceStateUseCase(
                get(DeviceRuntimeRepositoryPort, session=session),
                get(PrinterBindingRepositoryPort, session=session),
                get(UpsertPrinterRuntimeUseCase, session=session),
                get_domain_service(),
            ),
        )
    if interface is GetBindingByIpUseCase:
        return cast(T, GetBindingByIpUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is GetBindingByMacUseCase:
        return cast(T, GetBindingByMacUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is GetBindingBySerialUseCase:
        return cast(T, GetBindingBySerialUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is GetBindingByPrinterIdUseCase:
        return cast(T, GetBindingByPrinterIdUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is EnqueueStartPrintCommandUseCase:
        return cast(T, EnqueueStartPrintCommandUseCase(_command_queue))
    if interface is PopNextCommandUseCase:
        return cast(T, PopNextCommandUseCase(_command_queue))
    if interface is CreatePrinterJobUseCase:
        return cast(
            T,
            CreatePrinterJobUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                adapter_resolver=_printer_adapters,
            ),
        )
    if interface is GetPrinterMachineInfoUseCase:
        return cast(
            T,
            GetPrinterMachineInfoUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                adapter_resolver=_printer_adapters,
            ),
        )
    if interface is SyncPrinterStateUseCase:
        return cast(
            T,
            SyncPrinterStateUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                adapter_resolver=_printer_adapters,
                upsert_printer_runtime=get(UpsertPrinterRuntimeUseCase, session=session),
            ),
        )
    if interface is SetDeviceIgnoredUseCase:
        return cast(T, SetDeviceIgnoredUseCase(get(DeviceRuntimeRepositoryPort, session=session)))
    if interface is SetDeviceIgnoredByMacUseCase:
        return cast(T, SetDeviceIgnoredByMacUseCase(get(DeviceRuntimeRepositoryPort, session=session)))
    if interface is UnbindPrinterUseCase:
        return cast(
            T,
            UnbindPrinterUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                device_runtime_repo=get(DeviceRuntimeRepositoryPort, session=session),
            ),
        )
    if interface is DiscoverNetworkHostsUseCase:
        return cast(T, DiscoverNetworkHostsUseCase(arp_scanner=_arp_scanner, device_prober=_device_prober))
    if interface is RefreshNetworkDiscoveryUseCase:
        return cast(
            T,
            RefreshNetworkDiscoveryUseCase(
                discover_network_hosts=get(DiscoverNetworkHostsUseCase, session=session),
                discovery_snapshot=_discovery_snapshot,
                discovery_rows_builder=build_rows_from_discovery,
            ),
        )
    raise KeyError(f"Aucun binding pour {interface!r}")


def dep(interface: type[T]) -> Callable[..., T]:
    def _provider(session: Session = Depends(get_session)) -> T:
        return get(interface, session=session)

    return _provider

