import unittest

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import DwColumn, DwQueryResponse, DwSchemaResponse, DwTable
from backend.app.providers import BaseProvider, CompletionResult
from backend.app.services import WarehouseError, WarehouseService


class FakeProvider(BaseProvider):
    name = "fake"

    def health_check(self) -> bool:
        return True

    def chat_completion(self, model, messages, temperature=0.2, max_tokens=None):
        return CompletionResult(model=model, resposta="ok", metadados={"provider": self.name})


class FakeWarehouse:
    def ask(self, question, model=None, max_rows=None):
        return DwQueryResponse(
            status="ok",
            model=model or "qwen3.5:9b",
            resposta="Foram encontrados 2 registros.",
            sql="SELECT id FROM analytics.fact_vendas LIMIT 2",
            columns=["id"],
            rows=[[1], [2]],
            row_count=2,
            truncated=False,
            metadados={"read_only": True},
        )


class SequencedProvider(FakeProvider):
    def __init__(self):
        self.calls = 0

    def chat_completion(self, model, messages, temperature=0.2, max_tokens=None):
        self.calls += 1
        response = (
            '{"sql":"SELECT id FROM analytics.fact_vendas","explicacao":"Lista vendas."}'
            if self.calls == 1
            else "Foram encontrados dois registros de venda."
        )
        return CompletionResult(model=model, resposta=response, metadados={"provider": self.name})


def make_settings(**overrides):
    values = {
        "ENVIRONMENT": "development",
        "AUTH_ENABLED": False,
        "ADMIN_ENABLED": True,
        "ADMIN_API_KEY": "a" * 32,
        "PROVIDER": "ollama",
        "DEFAULT_CHAT_MODEL": "qwen3.5:9b",
        "DEFAULT_VISION_MODEL": "qwen3.5:9b",
        "FRONTEND_ENABLED": False,
        "DW_ENABLED": False,
    }
    values.update(overrides)
    return Settings(**values)


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(make_settings())
        self.app.state.provider = FakeProvider()
        self.app.state.warehouse_service = FakeWarehouse()
        self.client = TestClient(self.app)

    def test_admin_config_requires_admin_key(self):
        response = self.client.get("/admin/config")
        self.assertEqual(response.status_code, 401)

    def test_admin_config_never_returns_secrets(self):
        response = self.client.get("/admin/config", headers={"X-Admin-Key": "a" * 32})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("admin_api_key", body)
        self.assertNotIn("dw_password", body)
        self.assertFalse(body["dw_password_configured"])

    def test_dw_assistant_requires_admin_and_returns_auditable_sql(self):
        denied = self.client.post("/dw/ask", json={"pergunta": "Quantas vendas?"})
        self.assertEqual(denied.status_code, 401)

        response = self.client.post(
            "/dw/ask",
            headers={"X-Admin-Key": "a" * 32},
            json={"pergunta": "Quantas vendas?"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["metadados"]["read_only"])

    def test_cors_accepts_admin_header(self):
        response = self.client.options(
            "/admin/config",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Admin-Key",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("x-admin-key", response.headers["access-control-allow-headers"].lower())


class WarehouseSqlGuardTests(unittest.TestCase):
    def setUp(self):
        self.service = WarehouseService(FakeProvider(), make_settings())
        self.tables = [
            DwTable(
                schema_name="analytics",
                table_name="fact_vendas",
                table_type="BASE TABLE",
                columns=[DwColumn(name="id", data_type="bigint", nullable=False)],
            )
        ]

    def test_adds_safe_limit(self):
        sql = self.service._validate_sql("SELECT id FROM analytics.fact_vendas", self.tables, 50)
        self.assertIn("LIMIT 50", sql)

    def test_rejects_write(self):
        with self.assertRaises(WarehouseError):
            self.service._validate_sql("DELETE FROM analytics.fact_vendas", self.tables, 50)

    def test_rejects_table_outside_allowlist(self):
        with self.assertRaises(WarehouseError):
            self.service._validate_sql("SELECT id FROM public.usuarios", self.tables, 50)

    def test_rejects_dangerous_postgres_function(self):
        with self.assertRaises(WarehouseError):
            self.service._validate_sql("SELECT pg_sleep(10)", self.tables, 50)

    def test_full_question_pipeline_returns_sql_and_rows(self):
        provider = SequencedProvider()
        service = WarehouseService(provider, make_settings())
        service.get_schema = lambda force_refresh=False: DwSchemaResponse(
            status="ok",
            database="dw_test",
            user="reader",
            tables=self.tables,
        )
        service._execute_select = lambda sql, limit: (["id"], [[1], [2]], False)

        result = service.ask("Liste as vendas", max_rows=10)

        self.assertEqual(provider.calls, 2)
        self.assertEqual(result.row_count, 2)
        self.assertIn("LIMIT 10", result.sql)
        self.assertTrue(result.metadados["read_only"])


if __name__ == "__main__":
    unittest.main()
