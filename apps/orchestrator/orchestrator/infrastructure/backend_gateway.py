from orchestrator.infrastructure.backend_client import post_printer_state


class BackendGateway:
    def post_printer_state(self, printer_id: str, payload: dict) -> bool:
        return post_printer_state(printer_id, payload)



