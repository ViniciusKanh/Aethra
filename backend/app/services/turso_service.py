from dataclasses import dataclass
from typing import Any, Iterable

import requests

from .runtime_config_service import RuntimeConfigService, TursoRuntimeConfig


class TursoError(Exception):
    """Erro controlado da persistencia remota no Turso."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class TursoResult:
    rows: list[dict[str, Any]]
    affected_rows: int = 0


class TursoService:
    """Cliente sincrono e parametrizado para o protocolo SQL over HTTP do Turso."""

    def __init__(self, runtime_config_service: RuntimeConfigService, timeout: int = 30) -> None:
        self.runtime_config_service = runtime_config_service
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return self.runtime_config_service.get_turso_config().configured

    def initialize(self) -> None:
        if not self.configured:
            return
        statements = [
            ("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    failed_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """, []),
            ("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """, []),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)", []),
            ("CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)", []),
            ("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """, []),
            ("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at)", []),
            ("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
            """, []),
            ("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at)", []),
        ]
        self.pipeline(statements)

    def test_connection(self) -> dict[str, Any]:
        config = self._config()
        try:
            response = requests.get(
                f"{config.http_url}/health",
                headers={"Authorization": f"Bearer {config.auth_token}"},
                timeout=min(self.timeout, 15),
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise TursoError(503, "Nao foi possivel conectar ao banco Turso.") from exc
        return {"status": "online", "database_url": config.database_url, "encrypted": True}

    def execute(self, sql: str, args: Iterable[Any] = ()) -> TursoResult:
        return self.pipeline([(sql, list(args))])[0]

    def transaction(self, statements: list[tuple[str, list[Any]]]) -> list[TursoResult]:
        results = self.pipeline([("BEGIN IMMEDIATE", []), *statements, ("COMMIT", [])])
        return results[1:-1]

    def pipeline(self, statements: list[tuple[str, list[Any]]]) -> list[TursoResult]:
        config = self._config()
        requests_payload = [
            {
                "type": "execute",
                "stmt": {"sql": sql, "args": [self._encode_arg(value) for value in args]},
            }
            for sql, args in statements
        ]
        requests_payload.append({"type": "close"})
        try:
            response = requests.post(
                f"{config.http_url}/v2/pipeline",
                headers={
                    "Authorization": f"Bearer {config.auth_token}",
                    "Content-Type": "application/json",
                },
                json={"requests": requests_payload},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout as exc:
            raise TursoError(504, "O Turso excedeu o tempo limite da operacao.") from exc
        except (requests.RequestException, ValueError) as exc:
            raise TursoError(503, "Falha de comunicacao com o Turso.") from exc

        raw_results = payload.get("results")
        if not isinstance(raw_results, list) or len(raw_results) < len(statements):
            raise TursoError(502, "O Turso retornou uma resposta incompleta.")

        decoded: list[TursoResult] = []
        for item in raw_results[: len(statements)]:
            if item.get("type") != "ok":
                message = str(item.get("error", {}).get("message", ""))
                if "UNIQUE constraint failed" in message:
                    raise TursoError(409, "Registro duplicado no Turso.")
                raise TursoError(422, "O Turso rejeitou uma operacao de persistencia.")
            result = item.get("response", {}).get("result", {})
            columns = [str(column.get("name", "")) for column in result.get("cols", [])]
            rows = [
                {name: self._decode_value(value) for name, value in zip(columns, row)}
                for row in result.get("rows", [])
            ]
            decoded.append(TursoResult(rows=rows, affected_rows=int(result.get("affected_row_count", 0))))
        return decoded

    def _config(self) -> TursoRuntimeConfig:
        config = self.runtime_config_service.get_turso_config()
        if not config.configured:
            raise TursoError(503, "Configure a URL e o token do Turso no primeiro acesso.")
        return config

    @staticmethod
    def _encode_arg(value: Any) -> dict[str, Any]:
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "integer", "value": "1" if value else "0"}
        if isinstance(value, int):
            return {"type": "integer", "value": str(value)}
        if isinstance(value, float):
            return {"type": "float", "value": value}
        return {"type": "text", "value": str(value)}

    @staticmethod
    def _decode_value(value: dict[str, Any]) -> Any:
        value_type = value.get("type")
        if value_type == "null":
            return None
        if value_type == "integer":
            return int(value.get("value", 0))
        if value_type == "float":
            return float(value.get("value", 0))
        return value.get("value")
