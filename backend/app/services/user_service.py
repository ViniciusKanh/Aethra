import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import EmailStr, TypeAdapter
from pwdlib import PasswordHash

from ..config import Settings
from ..models import (
    AuthResponse,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    SetupAdminRequest,
    UserAdminUpdate,
    UserResponse,
)
from .turso_service import TursoError, TursoService


class AuthError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class UserService:
    """Identidades, bloqueio de login e sessoes persistidos exclusivamente no Turso."""

    def __init__(self, settings: Settings, turso_service: TursoService) -> None:
        self.settings = settings
        self.turso = turso_service
        self.password_hash = PasswordHash.recommended()
        self.email_adapter = TypeAdapter(EmailStr)

    def initialize(self) -> None:
        self.turso.initialize()
        if self.turso.configured:
            self._ensure_bootstrap_admin()

    def register(self, payload: RegisterRequest) -> AuthResponse:
        self._ensure_storage()
        if not self.settings.registration_enabled:
            raise AuthError(403, "Novos cadastros estao desativados.")
        if self.count_users() == 0:
            raise AuthError(409, "Crie primeiro a conta administrativa inicial.")
        email = self._normalize_email(payload.email)
        user = self._new_user(email, payload.display_name, payload.password, "user")
        try:
            self.turso.execute(
                """
                INSERT INTO users (id,email,display_name,password_hash,role,is_active,created_at,updated_at)
                VALUES (?, ?, ?, ?, 'user', 1, ?, ?)
                """,
                [user["id"], email, user["display_name"], user["password_hash"], user["created_at"], user["updated_at"]],
            )
        except TursoError as exc:
            if exc.status_code == 409:
                raise AuthError(409, "Ja existe uma conta com este e-mail.") from exc
            raise
        return self._create_session(user)

    def login(self, payload: LoginRequest) -> AuthResponse:
        self._ensure_storage()
        email = self._normalize_email(payload.email)
        self._delete_expired_sessions()
        rows = self.turso.execute("SELECT * FROM users WHERE email = ? LIMIT 1", [email]).rows
        if not rows:
            self.password_hash.hash(payload.password)
            raise AuthError(401, "E-mail ou senha invalidos.")
        row = rows[0]
        if not bool(row["is_active"]):
            raise AuthError(403, "Esta conta esta desativada.")

        now_dt = datetime.now(UTC)
        locked_until = self._parse_datetime(row.get("locked_until"))
        if locked_until and locked_until > now_dt:
            raise AuthError(429, "Conta temporariamente bloqueada por tentativas invalidas.")

        if not self.password_hash.verify(payload.password, str(row["password_hash"])):
            attempts = int(row.get("failed_attempts") or 0) + 1
            new_lock = None
            if attempts >= self.settings.max_login_attempts:
                new_lock = (now_dt + timedelta(minutes=self.settings.login_lock_minutes)).isoformat()
                attempts = 0
            self.turso.execute(
                "UPDATE users SET failed_attempts = ?, locked_until = ?, updated_at = ? WHERE id = ?",
                [attempts, new_lock, self._now(), row["id"]],
            )
            raise AuthError(401, "E-mail ou senha invalidos.")

        self.turso.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL, updated_at = ? WHERE id = ?",
            [self._now(), row["id"]],
        )
        row["failed_attempts"] = 0
        row["locked_until"] = None
        return self._create_session(row)

    def authenticate(self, token: str) -> UserResponse:
        self._ensure_storage()
        rows = self.turso.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            LIMIT 1
            """,
            [self._token_hash(token), self._now()],
        ).rows
        if not rows:
            raise AuthError(401, "Sessao ausente, expirada ou invalida.")
        row = rows[0]
        if not bool(row["is_active"]):
            self.turso.execute("DELETE FROM sessions WHERE user_id = ?", [row["id"]])
            raise AuthError(403, "Esta conta esta desativada.")
        return self._user_response(row)

    def logout(self, token: str) -> None:
        self._ensure_storage()
        self.turso.execute("DELETE FROM sessions WHERE token_hash = ?", [self._token_hash(token)])

    def setup_admin(self, payload: SetupAdminRequest, client_host: str) -> AuthResponse:
        self._ensure_storage()
        if client_host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            raise AuthError(403, "O primeiro administrador so pode ser criado em localhost.")
        if self.count_users() > 0:
            raise AuthError(409, "A configuracao inicial ja foi concluida.")
        email = self._normalize_email(payload.email)
        configured_email = self.settings.admin_email.strip().lower()
        if configured_email and email != configured_email:
            raise AuthError(403, "Use o e-mail administrativo configurado no servidor.")
        user = self._new_user(email, payload.display_name, payload.password, "admin")
        self.turso.execute(
            """
            INSERT INTO users (id,email,display_name,password_hash,role,is_active,created_at,updated_at)
            VALUES (?, ?, ?, ?, 'admin', 1, ?, ?)
            """,
            [user["id"], email, user["display_name"], user["password_hash"], user["created_at"], user["updated_at"]],
        )
        return self._create_session(user)

    def change_password(self, user_id: str, payload: PasswordChangeRequest) -> AuthResponse:
        rows = self.turso.execute("SELECT * FROM users WHERE id = ? LIMIT 1", [user_id]).rows
        if not rows or not self.password_hash.verify(payload.current_password, str(rows[0]["password_hash"])):
            raise AuthError(401, "Senha atual invalida.")
        row = rows[0]
        row["password_hash"] = self.password_hash.hash(payload.new_password)
        self.turso.transaction([
            ("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", [row["password_hash"], self._now(), user_id]),
            ("DELETE FROM sessions WHERE user_id = ?", [user_id]),
        ])
        return self._create_session(row)

    def update_user(self, actor_id: str, user_id: str, payload: UserAdminUpdate) -> UserResponse:
        if actor_id == user_id and payload.is_active is False:
            raise AuthError(422, "Voce nao pode desativar a propria conta.")
        rows = self.turso.execute("SELECT * FROM users WHERE id = ? LIMIT 1", [user_id]).rows
        if not rows:
            raise AuthError(404, "Usuario nao encontrado.")
        row = rows[0]
        new_role = payload.role or str(row["role"])
        new_active = int(payload.is_active if payload.is_active is not None else bool(row["is_active"]))
        if row["role"] == "admin" and new_role != "admin":
            admin_count = self.turso.execute(
                "SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND is_active = 1"
            ).rows[0]["total"]
            if int(admin_count) <= 1:
                raise AuthError(422, "A Aethra precisa manter ao menos um administrador ativo.")
        statements = [
            ("UPDATE users SET role = ?, is_active = ?, updated_at = ? WHERE id = ?", [new_role, new_active, self._now(), user_id])
        ]
        if not new_active:
            statements.append(("DELETE FROM sessions WHERE user_id = ?", [user_id]))
        self.turso.transaction(statements)
        row.update({"role": new_role, "is_active": new_active})
        return self._user_response(row)

    def list_users(self) -> list[UserResponse]:
        rows = self.turso.execute(
            "SELECT * FROM users ORDER BY CASE role WHEN 'admin' THEN 0 ELSE 1 END, created_at"
        ).rows
        return [self._user_response(row) for row in rows]

    def count_users(self) -> int:
        if not self.turso.configured:
            return 0
        rows = self.turso.execute("SELECT COUNT(*) AS total FROM users").rows
        return int(rows[0]["total"] if rows else 0)

    def _ensure_bootstrap_admin(self) -> None:
        email_value = self.settings.bootstrap_admin_email
        password = self.settings.bootstrap_admin_password
        if not email_value or not password:
            return
        email = self._normalize_email(self.email_adapter.validate_python(email_value))
        existing = self.turso.execute("SELECT * FROM users WHERE email = ? LIMIT 1", [email]).rows
        if existing:
            self.turso.execute(
                "UPDATE users SET role = 'admin', is_active = 1, updated_at = ? WHERE id = ?",
                [self._now(), existing[0]["id"]],
            )
            return
        user = self._new_user(email, email.split("@", 1)[0], password, "admin")
        self.turso.execute(
            """
            INSERT INTO users (id,email,display_name,password_hash,role,is_active,created_at,updated_at)
            VALUES (?, ?, ?, ?, 'admin', 1, ?, ?)
            """,
            [user["id"], email, user["display_name"], user["password_hash"], user["created_at"], user["updated_at"]],
        )

    def _new_user(self, email: str, name: str, password: str, role: str) -> dict[str, object]:
        now = self._now()
        return {
            "id": str(uuid4()),
            "email": email,
            "display_name": name.strip(),
            "password_hash": self.password_hash.hash(password),
            "role": role,
            "is_active": 1,
            "created_at": now,
            "updated_at": now,
        }

    def _create_session(self, row: dict[str, object]) -> AuthResponse:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(hours=self.settings.session_ttl_hours)
        self.turso.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            [self._token_hash(token), row["id"], expires_at.isoformat(), self._now()],
        )
        return AuthResponse(access_token=token, expires_at=expires_at.isoformat(), user=self._user_response(row))

    def _delete_expired_sessions(self) -> None:
        self.turso.execute("DELETE FROM sessions WHERE expires_at <= ?", [self._now()])

    def _ensure_storage(self) -> None:
        if not self.turso.configured:
            raise AuthError(503, "Configure o Turso para habilitar usuarios e sessoes.")

    @staticmethod
    def _user_response(row: dict[str, object]) -> UserResponse:
        return UserResponse(
            id=str(row["id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            role=str(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=str(row["created_at"]),
        )

    @staticmethod
    def _normalize_email(email: EmailStr | str) -> str:
        return str(email).strip().lower()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _parse_datetime(value: object | None) -> datetime | None:
        return datetime.fromisoformat(str(value)) if value else None
