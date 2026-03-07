from collections.abc import Callable
from typing import Any, TypeVar, cast

from fastapi import Depends
from sqlmodel import Session

from orchestrator.application.app_services import CommandQueueService, FleetViewService, OrchestratorNotificationService
from orchestrator.application.ports import (
    DiscoverySnapshotPort,
    NotificationPort,
    PrinterBindingRepositoryPort,
)
from orchestrator.application.use_cases import (
    CreatePrinterJobUseCase,
    EnqueueStartPrintCommandUseCase,
    GetBindingByPrinterIdUseCase,
    ListDeviceRuntimesUseCase,
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
    RefreshNetworkDiscoveryUseCase,
    SetDeviceIgnoredByMacUseCase,
    SetDeviceIgnoredUseCase,
    UnbindPrinterUseCase,
    UpsertBindingUseCase,
)
from orchestrator.domain.network_service import NetworkDiscoveryService
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.backend.gateway import BackendGateway
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.cache import build_rows_from_discovery
from orchestrator.infrastructure.network_discovery.device_probers import HttpDeviceProber
from orchestrator.infrastructure.network_discovery.snapshot_store import InMemoryDiscoverySnapshotStore
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter, notification_adapter
from orchestrator.infrastructure.persistence.db import get_session
from orchestrator.infrastructure.persistence.repositories import SqlModelPrinterBindingRepository
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


def get_network_service() -> NetworkDiscoveryService:
    return NetworkDiscoveryService(
        arp_scanner=_arp_scanner,
        device_prober=_device_prober,
    )


def get_binding_repo(session: Session = Depends(get_session)) -> PrinterBindingRepositoryPort:
    return SqlModelPrinterBindingRepository(session)


def get_fleet_view_service(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> FleetViewService:
    return FleetViewService(
        binding_repo=binding_repo,
        discovery_snapshot_provider=_discovery_snapshot.list_rows,
    )


def get_list_device_runtimes_use_case(
) -> ListDeviceRuntimesUseCase:
    return ListDeviceRuntimesUseCase(_discovery_snapshot.list_rows)


def get_list_device_binding_rows_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> ListDeviceBindingRowsUseCase:
    return ListDeviceBindingRowsUseCase(
        binding_repo=binding_repo,
        discovery_snapshot_provider=_discovery_snapshot.list_rows,
    )


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


def get_notification_adapter() -> WebSocketNotificationAdapter:
    return notification_adapter


def get_notification_port() -> NotificationPort:
    return notification_adapter


def get_orchestrator_notification_service(
    notification_port: NotificationPort = Depends(get_notification_port),
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> OrchestratorNotificationService:
    return OrchestratorNotificationService(
        notification_port=notification_port,
        list_fleet_use_case=list_fleet_use_case,
        list_unbound_ips_use_case=list_unbound_ips_use_case,
        list_device_binding_rows_use_case=list_device_binding_rows_use_case,
        machine_states_use_case=machine_states_use_case,
    )


def get_upsert_binding_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> UpsertBindingUseCase:
    return UpsertBindingUseCase(binding_repo, domain_service)


def get_binding_by_printer_id_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> GetBindingByPrinterIdUseCase:
    return GetBindingByPrinterIdUseCase(binding_repo)


def get_enqueue_start_command_use_case() -> EnqueueStartPrintCommandUseCase:
    return EnqueueStartPrintCommandUseCase(_command_queue)


def get_printer_adapter_registry() -> PrinterAdapterRegistry:
    return _printer_adapters


def get_create_printer_job_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    adapter_registry: PrinterAdapterRegistry = Depends(get_printer_adapter_registry),
) -> CreatePrinterJobUseCase:
    return CreatePrinterJobUseCase(
        binding_repo=binding_repo,
        adapter_resolver=adapter_registry,
        discovery_snapshot_provider=_discovery_snapshot.list_rows,
    )


def get_set_device_ignored_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> SetDeviceIgnoredUseCase:
    return SetDeviceIgnoredUseCase(binding_repo=binding_repo)


def get_set_device_ignored_by_mac_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> SetDeviceIgnoredByMacUseCase:
    return SetDeviceIgnoredByMacUseCase(binding_repo=binding_repo)


def get_unbind_printer_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
) -> UnbindPrinterUseCase:
    return UnbindPrinterUseCase(binding_repo=binding_repo)


def get_discovery_snapshot() -> DiscoverySnapshotPort:
    return _discovery_snapshot


def get_refresh_network_discovery_use_case(
    binding_repo: PrinterBindingRepositoryPort = Depends(get_binding_repo),
    discovery_snapshot: DiscoverySnapshotPort = Depends(get_discovery_snapshot),
    network_service: NetworkDiscoveryService = Depends(get_network_service),
    domain_service: OrchestratorDomainService = Depends(get_domain_service),
) -> RefreshNetworkDiscoveryUseCase:
    return RefreshNetworkDiscoveryUseCase(
        binding_repo=binding_repo,
        network_service=network_service,
        discovery_snapshot=discovery_snapshot,
        discovery_rows_builder=build_rows_from_discovery,
        domain_service=domain_service,
    )


def get(interface: type[T], session: Session | None = None) -> T:
    if interface is PrinterBindingRepositoryPort:
        if not session:
            raise ValueError("Session requise pour PrinterBindingRepositoryPort")
        return cast(T, SqlModelPrinterBindingRepository(session))
    if interface is FleetViewService:
        return cast(
            T,
            FleetViewService(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                discovery_snapshot_provider=_discovery_snapshot.list_rows,
            ),
        )
    if interface is ListDeviceRuntimesUseCase:
        return cast(T, ListDeviceRuntimesUseCase(_discovery_snapshot.list_rows))
    if interface is ListDeviceBindingRowsUseCase:
        return cast(
            T,
            ListDeviceBindingRowsUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                discovery_snapshot_provider=_discovery_snapshot.list_rows,
            ),
        )
    if interface is ListFleetUseCase:
        return cast(T, ListFleetUseCase(get(FleetViewService, session=session)))
    if interface is ListUnboundIpsUseCase:
        return cast(T, ListUnboundIpsUseCase(get(FleetViewService, session=session)))
    if interface is MachineStatesPayloadUseCase:
        return cast(T, MachineStatesPayloadUseCase(get(FleetViewService, session=session)))
    if interface is NotificationPort:
        return cast(T, notification_adapter)
    if interface is UpsertBindingUseCase:
        return cast(
            T,
            UpsertBindingUseCase(
                get(PrinterBindingRepositoryPort, session=session),
                get_domain_service(),
            ),
        )
    if interface is GetBindingByPrinterIdUseCase:
        return cast(T, GetBindingByPrinterIdUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is EnqueueStartPrintCommandUseCase:
        return cast(T, EnqueueStartPrintCommandUseCase(_command_queue))
    if interface is CreatePrinterJobUseCase:
        return cast(
            T,
            CreatePrinterJobUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                adapter_resolver=_printer_adapters,
                discovery_snapshot_provider=_discovery_snapshot.list_rows,
            ),
        )
    if interface is SetDeviceIgnoredUseCase:
        return cast(T, SetDeviceIgnoredUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is SetDeviceIgnoredByMacUseCase:
        return cast(T, SetDeviceIgnoredByMacUseCase(get(PrinterBindingRepositoryPort, session=session)))
    if interface is UnbindPrinterUseCase:
        return cast(
            T,
            UnbindPrinterUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
            ),
        )
    if interface is RefreshNetworkDiscoveryUseCase:
        return cast(
            T,
            RefreshNetworkDiscoveryUseCase(
                binding_repo=get(PrinterBindingRepositoryPort, session=session),
                network_service=get_network_service(),
                discovery_snapshot=_discovery_snapshot,
                discovery_rows_builder=build_rows_from_discovery,
                domain_service=get_domain_service(),
            ),
        )
    raise KeyError(f"Aucun binding pour {interface!r}")


def dep(interface: type[T]) -> Callable[..., T]:
    def _provider(session: Session = Depends(get_session)) -> T:
        return get(interface, session=session)

    return _provider

