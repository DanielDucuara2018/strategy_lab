import httpx
from typing import Literal, Any

BASE_URL = "https://api.telegram.org"
TELEGRAM_TIMEOUT = 30


class TelegramBot:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def url(self):
        return f"{BASE_URL}/bot{self.bot_token}"

    def _request(
        self,
        endpoint: str,
        *,
        body: dict | None = None,
        method: Literal["GET", "POST"] = "POST",
        transport: httpx.BaseTransport | None = None,
    ) -> dict[str, Any]:
        with httpx.Client(transport=transport, timeout=TELEGRAM_TIMEOUT) as client:
            response = client.request(method, f"{self.url}/{endpoint}", json=body)
        if response.status_code != httpx.codes.OK:
            msg = f"invalid HTTP status code - '{response.status_code}' - body: '{response.text}'"
            raise ConnectionError(msg)
        return response.json()

    def send_telegram_message(self, message: str) -> None:
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"}
        self._request("sendMessage", body=payload)
