"""Testes de `app/http/rotas_conta.py` contra Postgres real — RF-02, AC-03
(T-30).

Todos os testes exigem Postgres real (`@pytest.mark.requer_banco`), pulados
com mensagem explícita sem `DATABASE_URL` (hook de `tests/app_aluno/
conftest.py`), mesmo padrão de `tests/app_aluno/integracao/
test_persistencia_contas.py` (T-28) e `test_persistencia_casos.py` (T-23).

Cobre o que `tests/app_aluno/test_rotas_conta.py` (dublês em memória) não
pode provar: a transação ÚNICA de `_cadastrar_conta_e_caso_supabase` —
`UNIQUE` real de `email` recusando o `INSERT` de `contas` e, com ele, o
`INSERT` de `casos` na MESMA transação (nenhuma conta órfã sem caso, nenhum
caso órfão sem conta).

REGRAS: RF-02, AC-03
"""

from __future__ import annotations

import re
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.http.aplicacao import criar_aplicacao
from app.notificacao.email import EnviadorEmMemoria, obter_enviador

pytestmark = pytest.mark.requer_banco

_CHAVE_TESTE = "chave-de-teste-para-assinatura-de-sessao-nao-usar-em-producao"


def _database_url() -> str:
    from persistencia.supabase.conexao import obter_database_url

    return obter_database_url()


def _email_novo() -> str:
    return f"teste-t30-{uuid.uuid4().hex}@teste.invalido"


@pytest.fixture
def cliente(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    aplicacao = criar_aplicacao()
    return TestClient(aplicacao, base_url="https://teste.local")


def _contar_contas_por_email(email: str) -> int:
    with psycopg.connect(_database_url()) as conexao, conexao.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM piq_app_aluno.contas WHERE email = %s", (email,))
        linha = cursor.fetchone()
        assert linha is not None
        return int(linha[0])


def _contar_casos_por_conta_email(email: str) -> int:
    with psycopg.connect(_database_url()) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*) FROM piq_app_aluno.casos c
            JOIN piq_app_aluno.contas a ON a.conta_id = c.conta_id
            WHERE a.email = %s
            """,
            (email,),
        )
        linha = cursor.fetchone()
        assert linha is not None
        return int(linha[0])


# ---------------------------------------------------------------------------
# Critério 1 — cadastro cria conta e caso, atomicamente, contra banco real.
# ---------------------------------------------------------------------------


def test_cadastro_cria_conta_e_caso_em_cadastrado_no_banco_real(cliente: TestClient) -> None:
    email = _email_novo()

    resposta = cliente.post("/api/conta/cadastro", data={"email": email, "senha": "senhaForte123"})

    assert resposta.status_code == 201  # `201 Created` — o POST cria conta e caso
    assert _contar_contas_por_email(email) == 1
    assert _contar_casos_por_conta_email(email) == 1

    with psycopg.connect(_database_url()) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.estado FROM piq_app_aluno.casos c
            JOIN piq_app_aluno.contas a ON a.conta_id = c.conta_id
            WHERE a.email = %s
            """,
            (email,),
        )
        linha = cursor.fetchone()
        assert linha is not None
    assert linha[0] == "CADASTRADO"


def test_cadastro_com_email_duplicado_nao_deixa_conta_orfa_nem_caso_extra(
    cliente: TestClient,
) -> None:
    """A transação ÚNICA garante que a segunda tentativa (e-mail já
    existente) não grava NEM conta NEM caso extra — a violação de `UNIQUE`
    em `contas` faz `ROLLBACK` da transação inteira."""
    email = _email_novo()
    cliente.post("/api/conta/cadastro", data={"email": email, "senha": "primeiraSenha"})
    assert _contar_contas_por_email(email) == 1
    assert _contar_casos_por_conta_email(email) == 1

    resposta = cliente.post("/api/conta/cadastro", data={"email": email, "senha": "segundaSenha"})

    assert resposta.status_code == 400
    assert _contar_contas_por_email(email) == 1
    assert _contar_casos_por_conta_email(email) == 1


# ---------------------------------------------------------------------------
# Critérios 2 e 3 — login/logout ponta a ponta contra banco real.
# ---------------------------------------------------------------------------


def test_login_e_logout_ponta_a_ponta_contra_banco_real(cliente: TestClient) -> None:
    """`acesso-sem-senha` (T-692): o aluno entra só com o e-mail (`RF-701`);
    depois do logout, a sessão some."""
    email = _email_novo()
    cliente.post("/api/conta/cadastro", data={"email": email, "senha": "senhaCorreta"})
    cliente.post("/api/conta/logout")

    # `AC-711`: maiúsculas e espaços nas pontas não impedem a entrada.
    resposta_login = cliente.post(
        "/api/conta/login", data={"email": f"  {email.upper()} "}
    )
    assert resposta_login.status_code == 200
    assert cliente.get("/api/conta/eu").status_code == 200

    resposta_logout = cliente.post("/api/conta/logout")
    # A rota JSON não redireciona: o destino é decisão do cliente.
    assert resposta_logout.history == []
    assert cliente.get("/api/conta/eu").status_code == 401


# ---------------------------------------------------------------------------
# `acesso-sem-senha` (T-694) — `AC-712`: conta legada gravada com maiúsculas
# é encontrada pelo login e pelo webhook de reembolso (`RF-704`).
# ---------------------------------------------------------------------------


def test_ac712_conta_com_maiusculas_entra_e_e_bloqueada_pelo_reembolso(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sufixo = uuid.uuid4().hex
    conta_id = f"TESTE_T694_CONTA_{sufixo}"
    # SQL direto: o adaptador agora grava normalizado, e o caso é o legado.
    with psycopg.connect(_database_url()) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            "INSERT INTO piq_app_aluno.contas (conta_id, email, senha_hash, criado_em) "
            "VALUES (%s, %s, NULL, now())",
            (conta_id, f"Fulano-{sufixo}@Exemplo.com"),
        )

    resposta_login = cliente.post(
        "/api/conta/login", data={"email": f"fulano-{sufixo}@exemplo.com"}
    )
    assert resposta_login.status_code == 200
    assert resposta_login.json()["conta_id"] == conta_id

    monkeypatch.setenv("HOTMART_HOTTOK", "hottok-de-teste")
    monkeypatch.delenv("HOTMART_PRODUTO_ID", raising=False)
    resposta_reembolso = cliente.post(
        "/api/provisionamento/hotmart",
        json={
            "event": "PURCHASE_REFUNDED",
            "data": {"product": {"id": "1"}, "buyer": {"email": f"FULANO-{sufixo}@exemplo.com"}},
        },
        headers={"X-HOTMART-HOTTOK": "hottok-de-teste"},
    )
    assert resposta_reembolso.json() == {"bloqueado": True}

    with psycopg.connect(_database_url()) as conexao, conexao.cursor() as cursor:
        cursor.execute(
            "SELECT bloqueado_em FROM piq_app_aluno.contas WHERE conta_id = %s", (conta_id,)
        )
        linha = cursor.fetchone()
    assert linha is not None and linha[0] is not None


# ---------------------------------------------------------------------------
# `acesso-sem-senha` (T-698) — `AC-730`, `EC-701`: o revisor promovido sem
# senha cria a primeira pela recuperação e entra; tela e rota `/senha`
# inalteradas (`RF-711`).
# ---------------------------------------------------------------------------


def test_ac730_revisor_promovido_sem_senha_cria_a_primeira_e_entra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from persistencia.app_aluno.cadastro import provisionar_conta_e_caso
    from persistencia.app_aluno.contas import promover_a_revisor

    monkeypatch.setenv("CHAVE_ASSINATURA_SESSAO", _CHAVE_TESTE)
    monkeypatch.setenv("URL_BASE_APP", "https://piq.exemplo.br")
    enviador = EnviadorEmMemoria()
    aplicacao = criar_aplicacao()
    aplicacao.dependency_overrides[obter_enviador] = lambda: enviador
    cliente = TestClient(aplicacao, base_url="https://teste.local")

    conta, _caso = provisionar_conta_e_caso(_email_novo())
    promover_a_revisor(conta.email)

    # (1) só o e-mail ⇒ a tela pede a senha.
    etapa_email = cliente.post("/api/conta/login", data={"email": conta.email})
    assert etapa_email.status_code == 401
    assert etapa_email.json()["exige_senha"] is True

    # (2) recuperação ⇒ o link chega com o token no fragmento.
    recuperacao = cliente.post("/api/provisionamento/recuperacao", data={"email": conta.email})
    assert recuperacao.json() == {"pedido_registrado": True}
    ((destinatario, _assunto, corpo),) = enviador.enviados
    assert destinatario == conta.email
    achado = re.search(r"#definir-senha/(\S+)", corpo)
    assert achado is not None

    # (3) define a primeira senha.
    senha = cliente.post(
        "/api/provisionamento/senha",
        data={"token": achado.group(1), "senha": "senhaNovaDoRevisor"},
    )
    assert senha.status_code == 200
    assert senha.json() == {"senha_definida": True}

    # (4) e-mail e senha ⇒ entra como revisor.
    login = cliente.post(
        "/api/conta/login", data={"email": conta.email, "senha": "senhaNovaDoRevisor"}
    )
    assert login.status_code == 200
    assert login.json()["e_revisor"] is True
