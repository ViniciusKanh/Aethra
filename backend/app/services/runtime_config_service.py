import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Iterator

from cryptography.fernet import Fernet, InvalidToken

from ..config import Settings
from ..models import KnowledgeConfigUpdate, TursoConfigUpdate


class RuntimeConfigError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class TursoRuntimeConfig:
    database_url: str
    auth_token: str

    @property
    def configured(self) -> bool:
        return bool(self.database_url and self.auth_token)

    @property
    def http_url(self) -> str:
        if self.database_url.startswith("libsql://"):
            return "https://" + self.database_url.removeprefix("libsql://").rstrip("/")
        return self.database_url.rstrip("/")


@dataclass(frozen=True)
class KnowledgeRuntimeConfig:
    enabled: bool
    folder_id: str
    service_account_json: str
    embedding_model: str
    top_k: int
    chunk_size: int
    chunk_overlap: int

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.folder_id and self.service_account_json)

    @property
    def service_account_email(self) -> str | None:
        try:
            payload = json.loads(self.service_account_json)
        except (TypeError, json.JSONDecodeError):
            return None
        email = payload.get("client_email") if isinstance(payload, dict) else None
        return str(email) if email else None


class RuntimeConfigService:
    """Mantem apenas configuracoes e segredos locais criptografados."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_path = settings.resolved_local_config_db_path
        self.key_path = settings.resolve_local_path(settings.config_key_path)
        self._fernet: Fernet | None = None

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_config (
                    config_key TEXT PRIMARY KEY,
                    encrypted_value BLOB NOT NULL,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT
                )
                """
            )

    def get_turso_config(self) -> TursoRuntimeConfig:
        payload = self._read_payload("turso")
        if payload is None:
            return TursoRuntimeConfig(
                database_url=self.settings.turso_database_url.strip(),
                auth_token=self.settings.turso_auth_token.strip(),
            )
        try:
            return TursoRuntimeConfig(**payload)
        except (TypeError, ValueError) as exc:
            raise RuntimeConfigError(500, "A configuracao criptografada do Turso nao pode ser lida.") from exc

    def save_turso_config(
        self,
        payload: TursoConfigUpdate,
        updated_by: str | None = None,
    ) -> TursoRuntimeConfig:
        current = self.get_turso_config()
        token = payload.auth_token.strip() if payload.auth_token is not None else current.auth_token
        database_url = payload.database_url.strip()
        if not re.fullmatch(r"libsql://[A-Za-z0-9.-]+(?::\d+)?/?", database_url):
            raise RuntimeConfigError(422, "Informe uma URL Turso valida iniciada por libsql://.")
        if not token:
            raise RuntimeConfigError(422, "Informe o token de autenticacao do Turso.")
        config = TursoRuntimeConfig(database_url=database_url.rstrip("/"), auth_token=token)
        self._save_payload("turso", asdict(config), updated_by)
        return config

    def get_knowledge_config(self) -> KnowledgeRuntimeConfig:
        payload = self._read_payload("knowledge")
        if payload is None:
            return KnowledgeRuntimeConfig(
                enabled=False,
                folder_id="",
                service_account_json="",
                embedding_model=self.settings.default_embedding_model,
                top_k=6,
                chunk_size=1_200,
                chunk_overlap=180,
            )
        try:
            return KnowledgeRuntimeConfig(**payload)
        except (TypeError, ValueError) as exc:
            raise RuntimeConfigError(500, "A configuracao criptografada dos documentos nao pode ser lida.") from exc

    def save_knowledge_config(
        self,
        payload: KnowledgeConfigUpdate,
        updated_by: str,
    ) -> KnowledgeRuntimeConfig:
        current = self.get_knowledge_config()
        credentials_json = (
            payload.service_account_json.strip()
            if payload.service_account_json is not None
            else current.service_account_json
        )
        if payload.enabled and not credentials_json:
            raise RuntimeConfigError(422, "Informe o JSON da conta de servico do Google.")
        if credentials_json:
            try:
                credentials = json.loads(credentials_json)
            except json.JSONDecodeError as exc:
                raise RuntimeConfigError(422, "O JSON da conta de servico e invalido.") from exc
            required = {"type", "client_email", "private_key", "token_uri"}
            if not isinstance(credentials, dict) or credentials.get("type") != "service_account":
                raise RuntimeConfigError(422, "Use uma credencial JSON do tipo service_account.")
            if not required.issubset(credentials):
                raise RuntimeConfigError(422, "A credencial da conta de servico esta incompleta.")

        folder_value = payload.folder_id.strip()
        folder_match = re.search(r"/folders/([A-Za-z0-9_-]+)", folder_value)
        folder_id = folder_match.group(1) if folder_match else folder_value
        if not re.fullmatch(r"[A-Za-z0-9_-]{5,255}", folder_id):
            raise RuntimeConfigError(422, "Informe um ID ou link valido de pasta do Google Drive.")

        config = KnowledgeRuntimeConfig(
            enabled=payload.enabled,
            folder_id=folder_id,
            service_account_json=credentials_json,
            embedding_model=payload.embedding_model.strip(),
            top_k=payload.top_k,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
        )
        self._save_payload("knowledge", asdict(config), updated_by)
        self.delete("knowledge_status")
        return config

    def get_knowledge_status(self) -> dict[str, Any] | None:
        return self._read_payload("knowledge_status")

    def save_knowledge_status(self, payload: dict[str, Any], updated_by: str | None = None) -> None:
        self._save_payload("knowledge_status", payload, updated_by)

    def delete(self, key: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM runtime_config WHERE config_key = ?", (key,))

    def _read_payload(self, key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT encrypted_value FROM runtime_config WHERE config_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        try:
            decrypted = self._cipher().decrypt(row["encrypted_value"])
            payload = json.loads(decrypted.decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeConfigError(500, "Uma configuracao criptografada nao pode ser lida.") from exc

    def _save_payload(self, key: str, payload: dict[str, Any], updated_by: str | None) -> None:
        encrypted = self._cipher().encrypt(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_config (config_key, encrypted_value, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    encrypted_value = excluded.encrypted_value,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                (key, encrypted, datetime.now(UTC).isoformat(), updated_by),
            )

    def _load_or_create_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        return key

    def _cipher(self) -> Fernet:
        if self._fernet is None:
            raise RuntimeConfigError(500, "Armazenamento seguro ainda nao foi inicializado.")
        return self._fernet

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA journal_mode = WAL")
            with connection:
                yield connection
        finally:
            connection.close()
