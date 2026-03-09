import asyncio

from orchestrator.application.app_services.orchestrator_notification_service import OrchestratorNotificationService
from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases.refresh_network_discovery import RefreshNetworkDiscoveryUseCase
from orchestrator.domain.models import NetworkRange


class DiscoverDevicesUseCase:
    refresh_network_discovery_use_case: RefreshNetworkDiscoveryUseCase = autowired()
    notifications: OrchestratorNotificationService = autowired()

    async def execute(self, cidr: str, timeout_s: float) -> dict[str, int]:
        updated = await asyncio.to_thread(
            self.refresh_network_discovery_use_case.execute,
            NetworkRange.parse(cidr).cidr,
            timeout_s,
        )
        await self.notifications.notify_discovery_refreshed()
        return {"updated": int(updated)}
