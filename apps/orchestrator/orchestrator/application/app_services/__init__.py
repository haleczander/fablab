from importlib import import_module
from typing import Any

__all__ = ["CommandQueueService", "FleetViewService", "OrchestratorNotificationService"]


def __getattr__(name: str) -> Any:
    if name == "CommandQueueService":
        return import_module("orchestrator.application.app_services.command_queue").CommandQueueService
    if name == "FleetViewService":
        return import_module("orchestrator.application.app_services.fleet_view").FleetViewService
    if name == "OrchestratorNotificationService":
        return import_module(
            "orchestrator.application.app_services.orchestrator_notification_service"
        ).OrchestratorNotificationService
    raise AttributeError(name)

