from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from config import (
    ORCH_PRUSALINK_API_KEY,
    ORCH_PRUSALINK_PASSWORD,
    ORCH_PRUSALINK_TIMEOUT_S,
    ORCH_PRUSALINK_USERNAME,
)
from orchestrator.application.app_services.command_queue import CommandQueueService
from orchestrator.application.app_services.fleet_view import FleetViewService
from orchestrator.application.ports import (
    ArpNeighborScannerPort,
    DeviceProberPort,
    DiscoverySnapshotPort,
    NotificationPort,
    PrinterAdapterResolverPort,
    PrinterBindingPersistencePort,
)
from orchestrator.domain.network_service import NetworkDiscoveryService
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.device_probers import HttpDeviceProber
from orchestrator.infrastructure.network_discovery.snapshot_store import InMemoryDiscoverySnapshotStore
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter
from orchestrator.infrastructure.persistence import SqlModelPrinterBindingPersistenceAdapter
from orchestrator.infrastructure.printers.adapter_registry import PrinterAdapterRegistry
from orchestrator.infrastructure.printers.prusalink_adapter import PrusaLinkAdapter
from orchestrator.shared.autowired import BindingSpec, autowired as shared_autowired, registry

T = TypeVar("T")
Resolver = Callable[[], object] | BindingSpec

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

_notification_binding = BindingSpec(
    resolver=WebSocketNotificationAdapter,
    singleton=True,
)
_command_queue_binding = BindingSpec(
    resolver=CommandQueueService,
    singleton=True,
)
_discovery_snapshot_binding = BindingSpec(
    resolver=InMemoryDiscoverySnapshotStore,
    singleton=True,
)
_printer_registry_binding = BindingSpec(
    resolver=lambda: _printer_adapters,
    singleton=True,
)


def autowired() -> Any:
    return shared_autowired()


def _resolvers() -> dict[type[Any], Resolver]:
    from orchestrator.application.app_services.orchestrator_notification_service import (
        OrchestratorNotificationService as OrchestratorNotificationServiceRef,
    )
    from orchestrator.application.use_cases.create_printer_job import (
        CreatePrinterJobUseCase as CreatePrinterJobUseCaseRef,
    )
    from orchestrator.application.use_cases.discover_devices import (
        DiscoverDevicesUseCase as DiscoverDevicesUseCaseRef,
    )
    from orchestrator.application.use_cases.enqueue_start_print_command import (
        EnqueueStartPrintCommandUseCase as EnqueueStartPrintCommandUseCaseRef,
    )
    from orchestrator.application.use_cases.get_binding_by_printer_id import (
        GetBindingByPrinterIdUseCase as GetBindingByPrinterIdUseCaseRef,
    )
    from orchestrator.application.use_cases.list_bindings import (
        ListBindingsUseCase as ListBindingsUseCaseRef,
    )
    from orchestrator.application.use_cases.list_external_devices import (
        ListExternalDevicesUseCase as ListExternalDevicesUseCaseRef,
    )
    from orchestrator.application.use_cases.list_fleet import (
        ListFleetUseCase as ListFleetUseCaseRef,
    )
    from orchestrator.application.use_cases.list_unbound_ips import (
        ListUnboundIpsUseCase as ListUnboundIpsUseCaseRef,
    )
    from orchestrator.application.use_cases.machine_states_payload import (
        MachineStatesPayloadUseCase as MachineStatesPayloadUseCaseRef,
    )
    from orchestrator.application.use_cases.refresh_network_discovery import (
        RefreshNetworkDiscoveryUseCase as RefreshNetworkDiscoveryUseCaseRef,
    )
    from orchestrator.application.use_cases.start_print_command import (
        StartPrintCommandUseCase as StartPrintCommandUseCaseRef,
    )
    from orchestrator.application.use_cases.unbind_printer import (
        UnbindPrinterUseCase as UnbindPrinterUseCaseRef,
    )
    from orchestrator.application.use_cases.upsert_binding import (
        UpsertBindingUseCase as UpsertBindingUseCaseRef,
    )

    return {
        OrchestratorDomainService: OrchestratorDomainService,
        NetworkDiscoveryService: NetworkDiscoveryService,
        PrinterBindingPersistencePort: SqlModelPrinterBindingPersistenceAdapter,
        FleetViewService: FleetViewService,
        ListBindingsUseCaseRef: ListBindingsUseCaseRef,
        ListExternalDevicesUseCaseRef: ListExternalDevicesUseCaseRef,
        ListFleetUseCaseRef: ListFleetUseCaseRef,
        ListUnboundIpsUseCaseRef: ListUnboundIpsUseCaseRef,
        MachineStatesPayloadUseCaseRef: MachineStatesPayloadUseCaseRef,
        NotificationPort: _notification_binding,
        WebSocketNotificationAdapter: _notification_binding,
        OrchestratorNotificationServiceRef: OrchestratorNotificationServiceRef,
        CommandQueueService: _command_queue_binding,
        EnqueueStartPrintCommandUseCaseRef: EnqueueStartPrintCommandUseCaseRef,
        GetBindingByPrinterIdUseCaseRef: GetBindingByPrinterIdUseCaseRef,
        CreatePrinterJobUseCaseRef: CreatePrinterJobUseCaseRef,
        UpsertBindingUseCaseRef: UpsertBindingUseCaseRef,
        UnbindPrinterUseCaseRef: UnbindPrinterUseCaseRef,
        ArpNeighborScannerPort: ScapyArpNeighborScanner,
        DeviceProberPort: HttpDeviceProber,
        PrinterAdapterResolverPort: _printer_registry_binding,
        PrinterAdapterRegistry: _printer_registry_binding,
        DiscoverySnapshotPort: _discovery_snapshot_binding,
        RefreshNetworkDiscoveryUseCaseRef: RefreshNetworkDiscoveryUseCaseRef,
        DiscoverDevicesUseCaseRef: DiscoverDevicesUseCaseRef,
        StartPrintCommandUseCaseRef: StartPrintCommandUseCaseRef,
    }


registry.register_many(_resolvers())


def get(interface: type[T]) -> T:
    return registry.get(interface)
