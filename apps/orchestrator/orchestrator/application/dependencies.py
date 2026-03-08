from __future__ import annotations

import inspect
from importlib import import_module
from collections.abc import Callable
from typing import Any, TypeVar, cast, get_args, get_origin, get_type_hints

from config import (
    ORCH_PRUSALINK_API_KEY,
    ORCH_PRUSALINK_PASSWORD,
    ORCH_PRUSALINK_TIMEOUT_S,
    ORCH_PRUSALINK_USERNAME,
)
from orchestrator.application.app_services.command_queue import CommandQueueService
from orchestrator.application.app_services.fleet_view import FleetViewService
from orchestrator.application.ports import (
    DiscoverySnapshotPort,
    NotificationPort,
    PrinterAdapterResolverPort,
    PrinterBindingPersistencePort,
)
from orchestrator.domain.network_service import NetworkDiscoveryService
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.network_discovery.arp_scanner import ScapyArpNeighborScanner
from orchestrator.infrastructure.network_discovery.cache import build_rows_from_discovery
from orchestrator.infrastructure.network_discovery.device_probers import HttpDeviceProber
from orchestrator.infrastructure.network_discovery.snapshot_store import InMemoryDiscoverySnapshotStore
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter, notification_adapter
from orchestrator.infrastructure.persistence import SqlModelPrinterBindingPersistenceAdapter
from orchestrator.infrastructure.printers.adapter_registry import PrinterAdapterRegistry
from orchestrator.infrastructure.printers.prusalink_adapter import PrusaLinkAdapter

T = TypeVar("T")
Resolver = Callable[[], object]

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


def _normalize_annotation(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) == 1:
        return args[0]
    return annotation


def discovery_snapshot_provider() -> Callable[[], list[dict[str, str | bool | int | float | None]]]:
    return _discovery_snapshot.list_rows


def discovery_rows_builder() -> Callable[[Any], list[dict[str, str | bool | int | float | None]]]:
    return build_rows_from_discovery


class _AutowiredDescriptor:
    def __set_name__(self, owner: type[object], name: str) -> None:
        self._name = name
        self._cache_name = f"__autowired_{name}"

    def __get__(self, instance: object | None, owner: type[object]) -> Any:
        if instance is None:
            return self
        cached = getattr(instance, self._cache_name, None)
        if cached is not None:
            return cached
        hints = get_type_hints(owner)
        dependency_type = _normalize_annotation(hints.get(self._name, inspect.Signature.empty))
        if dependency_type is inspect.Signature.empty:
            raise AttributeError(f"Aucune annotation pour {owner.__name__}.{self._name}")
        value = get(dependency_type)
        setattr(instance, self._cache_name, value)
        return value


def autowired() -> Any:
    return _AutowiredDescriptor()


printer_binding_persistence_adapter = lambda: SqlModelPrinterBindingPersistenceAdapter()
network_discovery_service = lambda: NetworkDiscoveryService(
    arp_scanner=_arp_scanner,
    device_prober=_device_prober,
)
fleet_view_service = lambda: FleetViewService(
    binding_repo=printer_binding_persistence_adapter(),
    discovery_snapshot_provider=_discovery_snapshot.list_rows,
)
websocket_notification_adapter = lambda: notification_adapter
notification_port = lambda: notification_adapter
orchestrator_domain_service = lambda: OrchestratorDomainService()
command_queue_service = lambda: _command_queue
printer_adapter_registry = lambda: _printer_adapters
discovery_snapshot_port = lambda: _discovery_snapshot
list_bindings_use_case = lambda: __import__(
    "orchestrator.application.use_cases.list_bindings", fromlist=["ListBindingsUseCase"]
).ListBindingsUseCase()
list_external_devices_use_case = lambda: __import__(
    "orchestrator.application.use_cases.list_external_devices", fromlist=["ListExternalDevicesUseCase"]
).ListExternalDevicesUseCase()
list_fleet_use_case = lambda: __import__(
    "orchestrator.application.use_cases.list_fleet", fromlist=["ListFleetUseCase"]
).ListFleetUseCase()
list_unbound_ips_use_case = lambda: __import__(
    "orchestrator.application.use_cases.list_unbound_ips", fromlist=["ListUnboundIpsUseCase"]
).ListUnboundIpsUseCase()
machine_states_payload_use_case = lambda: __import__(
    "orchestrator.application.use_cases.machine_states_payload", fromlist=["MachineStatesPayloadUseCase"]
).MachineStatesPayloadUseCase()
enqueue_start_print_command_use_case = lambda: __import__(
    "orchestrator.application.use_cases.enqueue_start_print_command", fromlist=["EnqueueStartPrintCommandUseCase"]
).EnqueueStartPrintCommandUseCase()
get_binding_by_printer_id_use_case = lambda: __import__(
    "orchestrator.application.use_cases.get_binding_by_printer_id", fromlist=["GetBindingByPrinterIdUseCase"]
).GetBindingByPrinterIdUseCase()
create_printer_job_use_case = lambda: __import__(
    "orchestrator.application.use_cases.create_printer_job", fromlist=["CreatePrinterJobUseCase"]
).CreatePrinterJobUseCase()
upsert_binding_use_case = lambda: __import__(
    "orchestrator.application.use_cases.upsert_binding", fromlist=["UpsertBindingUseCase"]
).UpsertBindingUseCase()
unbind_printer_use_case = lambda: __import__(
    "orchestrator.application.use_cases.unbind_printer", fromlist=["UnbindPrinterUseCase"]
).UnbindPrinterUseCase()
refresh_network_discovery_use_case = lambda: __import__(
    "orchestrator.application.use_cases.refresh_network_discovery", fromlist=["RefreshNetworkDiscoveryUseCase"]
).RefreshNetworkDiscoveryUseCase()
discover_devices_use_case = lambda: __import__(
    "orchestrator.application.use_cases.discover_devices", fromlist=["DiscoverDevicesUseCase"]
).DiscoverDevicesUseCase()
start_print_command_use_case = lambda: __import__(
    "orchestrator.application.use_cases.start_print_command", fromlist=["StartPrintCommandUseCase"]
).StartPrintCommandUseCase()
orchestrator_notification_service = lambda: __import__(
    "orchestrator.application.app_services.orchestrator_notification_service",
    fromlist=["OrchestratorNotificationService"],
).OrchestratorNotificationService()


def _resolvers() -> dict[type[Any], Resolver]:
    ListBindingsUseCase = import_module("orchestrator.application.use_cases.list_bindings").ListBindingsUseCase
    ListExternalDevicesUseCase = import_module(
        "orchestrator.application.use_cases.list_external_devices"
    ).ListExternalDevicesUseCase
    ListFleetUseCase = import_module("orchestrator.application.use_cases.list_fleet").ListFleetUseCase
    ListUnboundIpsUseCase = import_module("orchestrator.application.use_cases.list_unbound_ips").ListUnboundIpsUseCase
    MachineStatesPayloadUseCase = import_module(
        "orchestrator.application.use_cases.machine_states_payload"
    ).MachineStatesPayloadUseCase
    EnqueueStartPrintCommandUseCase = import_module(
        "orchestrator.application.use_cases.enqueue_start_print_command"
    ).EnqueueStartPrintCommandUseCase
    GetBindingByPrinterIdUseCase = import_module(
        "orchestrator.application.use_cases.get_binding_by_printer_id"
    ).GetBindingByPrinterIdUseCase
    CreatePrinterJobUseCase = import_module("orchestrator.application.use_cases.create_printer_job").CreatePrinterJobUseCase
    UpsertBindingUseCase = import_module("orchestrator.application.use_cases.upsert_binding").UpsertBindingUseCase
    UnbindPrinterUseCase = import_module("orchestrator.application.use_cases.unbind_printer").UnbindPrinterUseCase
    RefreshNetworkDiscoveryUseCase = import_module(
        "orchestrator.application.use_cases.refresh_network_discovery"
    ).RefreshNetworkDiscoveryUseCase
    DiscoverDevicesUseCase = import_module("orchestrator.application.use_cases.discover_devices").DiscoverDevicesUseCase
    StartPrintCommandUseCase = import_module(
        "orchestrator.application.use_cases.start_print_command"
    ).StartPrintCommandUseCase
    OrchestratorNotificationService = import_module(
        "orchestrator.application.app_services.orchestrator_notification_service"
    ).OrchestratorNotificationService

    return {
        OrchestratorDomainService: orchestrator_domain_service,
        NetworkDiscoveryService: network_discovery_service,
        PrinterBindingPersistencePort: printer_binding_persistence_adapter,
        FleetViewService: fleet_view_service,
        ListBindingsUseCase: list_bindings_use_case,
        ListExternalDevicesUseCase: list_external_devices_use_case,
        ListFleetUseCase: list_fleet_use_case,
        ListUnboundIpsUseCase: list_unbound_ips_use_case,
        MachineStatesPayloadUseCase: machine_states_payload_use_case,
        NotificationPort: notification_port,
        WebSocketNotificationAdapter: websocket_notification_adapter,
        OrchestratorNotificationService: orchestrator_notification_service,
        CommandQueueService: command_queue_service,
        EnqueueStartPrintCommandUseCase: enqueue_start_print_command_use_case,
        GetBindingByPrinterIdUseCase: get_binding_by_printer_id_use_case,
        CreatePrinterJobUseCase: create_printer_job_use_case,
        UpsertBindingUseCase: upsert_binding_use_case,
        UnbindPrinterUseCase: unbind_printer_use_case,
        PrinterAdapterResolverPort: printer_adapter_registry,
        PrinterAdapterRegistry: printer_adapter_registry,
        DiscoverySnapshotPort: discovery_snapshot_port,
        RefreshNetworkDiscoveryUseCase: refresh_network_discovery_use_case,
        DiscoverDevicesUseCase: discover_devices_use_case,
        StartPrintCommandUseCase: start_print_command_use_case,
    }


def get(interface: type[T]) -> T:
    resolver = _resolvers().get(interface)
    if resolver is None:
        raise KeyError(f"Aucun binding pour {interface!r}")
    return cast(T, resolver())
