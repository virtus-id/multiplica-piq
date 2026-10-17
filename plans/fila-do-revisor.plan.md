# Plano: fila do revisor em tabela

Rastreia a spec [`specs/fila-do-revisor.spec.md`](../specs/fila-do-revisor.spec.md).

## 1. Estratégia

Duas fatias: (A) leitura unificada no servidor, sem mexer no que existe; (B) a tabela no front. A rota antiga
`/api/revisao/fila` e a tela de conferência do caso não mudam.

## 2. Architecture

`app/revisao/lista_de_casos.py` (nova) monta a lista a partir de repositórios já existentes. Rota nova
`GET /api/revisao/casos` em `app/http/rotas_api_plano.py`, protegida por `exigir_papel_revisor`. Serialização em
`app/http/serializacao_plano.py`. No front, `TelaRevisao.tsx` passa a renderizar tabela (`TabelaDeCasos`),
barra de filtros e paginação; `api.ts` ganha `obterCasosParaRevisao`.

## 3. Tech Stack

Python/FastAPI e SQL já usados; React com Tailwind e o componente `Icone`. Sem dependência nova.

## 4. Data Model

Sem tabela nem coluna nova. Fontes: `casos` (estado, criação), `contas` (e-mail, nome), `eventos_caso` (entrada em
`AGUARDANDO_REVISAO`, `ocorrido_em`), `revisoes` (decisão, autor, `decidido_em`) e o último snapshot do caso
(método, dívidas, situação do mês).

## 5. Data Flow

Revisor abre a tela, o front chama `GET /api/revisao/casos` com aba, filtros, ordem e página; o servidor consulta
os casos dos estados incluídos, completa e-mail e nome, data de chegada, decisão e snapshot em lotes, filtra, ordena
e pagina; devolve itens, total e contagens por aba; o front guarda os filtros em `sessionStorage`.

## 6. Error Handling

401 sem sessão e 403 sem papel, com as mensagens atuais; falha de consulta mostra o bloco de erro com "Tentar de
novo"; parâmetros inválidos dão 422 sem expor detalhe interno.

## 7. Testing Strategy

Testes de servidor por critério (AC-501 a AC-505, AC-507); testes do componente e dos filtros no front; testes
estáticos existentes (sinais separados, sem aritmética sobre snapshot, linguagem humana, tokens, 360px, iconografia).

## 8. Traceability

| Requisito | Tarefa |
|---|---|
| RF-501, RF-503, RF-506 | T-408 |
| RF-502, RF-504, RF-505 | T-408, T-409 |
| RF-507 | T-409 |
| AC-501 a AC-507 | T-408, T-409, T-410 |
