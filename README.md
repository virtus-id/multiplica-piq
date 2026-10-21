# SDD Base — Kit Spec-Driven Development para Claude Code

Kit reutilizável para conduzir qualquer projeto pelo fluxo
**Discovery → Spec → Plan → Tasks → Code → Test → Review**, com subagentes e
slash commands do Claude Code.

**Agnóstico de stack.** Tudo que é específico do projeto vive em um único
arquivo: [`sdd.config.md`](sdd.config.md). Agentes e comandos nunca conhecem sua
stack — eles leem o config.

---

## Como usar em um projeto novo

```bash
# 1. Copie o kit para dentro do seu projeto
cp -r sdd-base/.claude       meu-projeto/
cp -r sdd-base/templates     meu-projeto/
cp -r sdd-base/specs         meu-projeto/
cp -r sdd-base/plans         meu-projeto/
cp -r sdd-base/tasks         meu-projeto/
cp    sdd-base/sdd.config.md meu-projeto/
cp    sdd-base/CLAUDE.md     meu-projeto/   # ou cole o conteúdo no CLAUDE.md existente

# opcional, se usa GitHub Actions
cp -r sdd-base/.github       meu-projeto/
```

No PowerShell:

```powershell
Copy-Item -Recurse sdd-base\.claude, sdd-base\templates, sdd-base\specs, sdd-base\plans, sdd-base\tasks -Destination meu-projeto\
Copy-Item sdd-base\sdd.config.md, sdd-base\CLAUDE.md -Destination meu-projeto\
```

Depois, dentro do projeto, rode:

```
/sdd:config  <descrição do projeto em uma linha>
```

Ele lê o repositório, detecta o que dá para detectar, **pergunta o resto em
opções** e escreve o `sdd.config.md` por você. **Esse é todo o setup.** Pode
rodar de novo quando quiser — ele atualiza em vez de recomeçar.

> **Stack não entra no config.** Linguagem, framework e bibliotecas são decisão
> de refinamento técnico e vivem na seção `Tech Stack` de
> `plans/<slug>.plan.md`, onde cada escolha se justifica contra um requisito.

---

## O ciclo de uma feature

```
/sdd:discovery  busca-de-cidade  "usuários não acham a cidade certa"
/sdd:spec       busca-de-cidade
/sdd:plan       busca-de-cidade
/sdd:tasks      busca-de-cidade
/sdd:implement  busca-de-cidade  next
/sdd:test       busca-de-cidade
/sdd:review     busca-de-cidade
/sdd:status
```

Cada feature tem um **slug** em `kebab-case`. Os artefatos dela:

| Etapa     | Arquivo                     |
| --------- | --------------------------- |
| Discovery | `specs/<slug>.discovery.md` |
| Spec      | `specs/<slug>.spec.md`      |
| Plan      | `plans/<slug>.plan.md`      |
| Tasks     | `tasks/<slug>.tasks.md`     |

Para features pequenas, `/sdd:discovery` é opcional — comece pela spec.

---

## Comandos

| Comando          | Faz                                                        |
| ---------------- | ---------------------------------------------------------- |
| `/sdd:config`    | Preenche o `sdd.config.md` perguntando (re-executável)     |
| `/sdd:discovery` | Levanta problema, personas, restrições e perguntas abertas |
| `/sdd:spec`      | Gera a especificação com requisitos e critérios de aceite  |
| `/sdd:plan`      | Gera o plano técnico com arquitetura e contratos           |
| `/sdd:tasks`     | Quebra o plano em backlog `T-NN` rastreável                |
| `/sdd:implement` | Implementa `T-NN`, um intervalo, ou `next`                 |
| `/sdd:test`      | Gera testes a partir dos critérios de aceite               |
| `/sdd:review`    | Revisa o diff contra spec, plano e convenções              |
| `/sdd:status`    | Mostra progresso e **furos de rastreabilidade**            |

## Agentes

Seis subagentes em `.claude/agents/`, um por fase, com ferramentas restritas ao
que a fase precisa — o Spec Agent não roda comandos, o Review Agent não edita
arquivos.

`sdd-spec` · `sdd-plan` · `sdd-task` · `sdd-code` · `sdd-test` · `sdd-review`

Os comandos já delegam ao agente certo. Para chamar direto:
`use o subagente sdd-review para revisar o diff atual`.

---

## Estrutura do kit

```
.claude/
  agents/          6 personas, uma por fase do fluxo
  commands/sdd/    9 slash commands /sdd:*
templates/         estrutura obrigatória de discovery, spec, plan e tasks
specs/  plans/  tasks/    onde os artefatos nascem
sdd.config.md      ⭐ o único arquivo a preencher
CLAUDE.md          regras do fluxo, carregadas automaticamente
.github/           validação em CI + template de PR (opcional)
```

---

## O que faz o kit funcionar

**Rastreabilidade em cadeia.** Requisito `RF-NN` → seção do plano → tarefa
`T-NN` → teste do critério `AC-NN`. Cada etapa produz uma tabela de cobertura, e
`/sdd:status` mostra onde a cadeia quebrou. É o que impede requisito de
evaporar entre a spec e o deploy.

**Ordem imposta, não sugerida.** Comandos param quando o artefato anterior não
existe. A CI reprova plano sem spec e tarefa sem plano.

**Ambiguidade explícita.** `Open Questions` é seção obrigatória. O Spec Agent
registra o que não sabe em vez de inventar — e reporta antes de você seguir.

**Escopo fechado.** O Code Agent implementa a tarefa e nada além. Trabalho
descoberto no caminho vira tarefa nova, com ID novo.

**Verificação real.** Nenhuma tarefa é marcada concluída sem os comandos do
config terem rodado. Falhou, o relatório traz a saída real.

---

## Personalizando

| Quero…                              | Mexo em…                              |
| ----------------------------------- | ------------------------------------- |
| Trocar comandos, convenções, restrições | `/sdd:config` — não edite na mão  |
| Trocar a stack                      | seção `Tech Stack` do plano da feature |
| Mudar as seções de uma spec/plano   | `templates/*.template.md`             |
| Mudar como uma fase se comporta     | `.claude/agents/sdd-*.md`             |
| Adicionar uma fase ao fluxo         | agente novo + comando novo em `.claude/commands/sdd/` |
| Afrouxar/apertar a validação em CI  | `.github/workflows/sdd-validate.yml`  |

> Os agentes aceleram, mas **você** é o(a) engenheiro(a) responsável. Revise
> criticamente cada artefato antes de aceitar.

---

## Segredos e deploy (SOPS + age)

Os segredos do PIQ ficam em `segredos.enc.env`: **criptografados e versionados**. Os nomes das
variáveis aparecem, os valores não. Não existe `.env` no servidor. O modelo com a explicação de
cada variável continua em [`.env.example`](.env.example).

```
 chave pública  ──fecha──►  segredos.enc.env  (no git)
 chave PRIVADA  ──abre───►  variáveis só na memória do processo ──► container
```

### Chaves

| Chave | Onde fica | Para quê |
|---|---|---|
| privada do **servidor** | `~/.config/sops/age/keys.txt` no servidor | subir o projeto |
| privada **pessoal** | `~/.config/sops/age/keys.txt` no Mac **e no gerenciador de senhas** | editar e recuperar |
| públicas (as duas) | [`.sops.yaml`](.sops.yaml) | criptografar. Não são segredo |

**A chave privada é a única coisa a proteger.** Perdendo as duas, o `segredos.enc.env` é
irrecuperável e todo valor precisa ser gerado de novo. Mantenha cópia fora do servidor e nunca
a envie ao git ou a um chat.

### Variáveis

| Variável | O que é |
|---|---|
| `DATABASE_URL` | Postgres do Supabase, **Session pooler (porta 5432)** |
| `CHAVE_ASSINATURA_SESSAO` | assina o cookie; trocar desloga todos |
| `PARAMETROS_VERSION_VIGENTE` | versão dos parâmetros (`1.0.1`); deve existir em `motor_calculo.parametros` |
| `URL_BASE_APP` | domínio público, **sem barra no fim** |
| `SEGREDO_PROVISIONAMENTO` | senha que a automação (n8n) envia para criar contas |
| `SMTP_SERVIDOR`, `SMTP_PORTA` | AWS SES por SMTP |
| `SMTP_USUARIO` | 20 caracteres, começa com `AKIA` |
| `SMTP_SENHA` | 44 caracteres, começa com `B` (não é a secret key do IAM) |
| `SMTP_REMETENTE` | "De:" verificado no SES |
| `HOTMART_HOTTOK`, `HOTMART_PRODUTO_ID` | webhook da Hotmart; o produto filtra compras de outros produtos |

Faltando uma obrigatória, a aplicação falha ao subir e nomeia a variável.

### Dia a dia

```bash
sops segredos.enc.env          # abre o editor e criptografa ao salvar (Mac)
git add segredos.enc.env && git commit && git push
```

No servidor, sem deixar `.env` no disco:

```bash
cd ~/workspace/multiplica-piq && git pull
sops exec-env segredos.enc.env 'docker compose up -d --build'
```

O compose repassa as variáveis ao container (`environment:`). Rodar `docker compose up` **sem** o
`sops exec-env` recria o container com variáveis vazias. `docker compose restart` é seguro.

### Servidor novo (recuperação)

```bash
git clone git@github.com:virtus-id/multiplica-piq.git ~/workspace/multiplica-piq
mkdir -p ~/.config/sops/age && chmod 700 ~/.config/sops/age
# colar a chave privada pessoal (gerenciador de senhas) em ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
cd ~/workspace/multiplica-piq && sops exec-env segredos.enc.env 'docker compose up -d --build'
```

Para o servidor novo ter a própria chave: `age-keygen -o ~/.config/sops/age/keys.txt`, troque a
pública antiga em `.sops.yaml` pela nova e rode `sops updatekeys segredos.enc.env`.

### Instalar as ferramentas

- Mac: `brew install sops age`. O SOPS procura a chave em
  `~/Library/Application Support/sops/age/keys.txt`:
  `ln -s ~/.config/sops/age/keys.txt "$HOME/Library/Application Support/sops/age/keys.txt"`.
- Ubuntu: `apt install age` e baixar o binário do SOPS em github.com/getsops/sops/releases.

### Se uma chave vazar

Troque a chave (`sops updatekeys`) **e** os valores que ela abria (senha do banco, SMTP,
segredos). O histórico do git guarda as versões antigas; trocar só a chave não basta.

### Dar acesso a outro desenvolvedor

A chave de cada pessoa é **dela**: nunca se compartilha a privada. O fluxo é gerar a chave, enviar
só a **pública** e quem já tem acesso a autoriza no `.sops.yaml`.

**1. Quem vai receber o acesso (gerar a chave)**

```bash
# instalar: brew install sops age   (Mac)  |  apt install age + binário do SOPS (Ubuntu)
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
age-keygen -y ~/.config/sops/age/keys.txt     # imprime a chave PÚBLICA (age1...): enviar essa
```

| Arquivo | O que é | Pode compartilhar? |
|---|---|---|
| `~/.config/sops/age/keys.txt` | **chave privada** (`AGE-SECRET-KEY-1...`) + a pública | **não**: guardar também no gerenciador de senhas |
| linha `age1...` (saída do `-y`) | chave **pública** | sim, é o que se envia |

No Mac, o SOPS procura a chave em outro caminho; crie o atalho:

```bash
mkdir -p "$HOME/Library/Application Support/sops/age"
ln -s ~/.config/sops/age/keys.txt "$HOME/Library/Application Support/sops/age/keys.txt"
```

Alternativa em qualquer sistema: `export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt`.

**2. Quem já tem acesso (autorizar)**

O arquivo é [`.sops.yaml`](.sops.yaml), na raiz do projeto, e não é criptografado. Acrescente a
chave pública da pessoa no fim da lista `age:`, separada por vírgula:

```yaml
creation_rules:
  - path_regex: segredos\.enc\.env$
    age: >-
      age1...servidor...,
      age1...voce...,
      age1...nova-pessoa...
```

Só editar o `.sops.yaml` **não basta**: é preciso recriptografar o arquivo de segredos.

```bash
sops updatekeys segredos.enc.env      # confirme com "y"
git add .sops.yaml segredos.enc.env && git commit -m "chore: dá acesso aos segredos a <nome>" && git push
```

A pessoa faz `git pull` e já abre com `sops segredos.enc.env`. Ela também precisa de acesso ao
repositório no GitHub (o SOPS não dá isso).

Observações:

- O acesso é ao arquivo **inteiro** (banco, SMTP, Hotmart), não por variável.
- Os commits antigos continuam fechados para a pessoa nova: ela abre só a versão atual em diante.
- **Remover alguém:** tire a pública dela do `.sops.yaml`, rode `sops updatekeys segredos.enc.env` e
  **troque os valores** (senha do banco, SMTP, segredos). Ela já viu os valores atuais.

### Rodar os containers na mão

No servidor (`ssh multiplica`), dentro da pasta de cada projeto em `~/workspace/`:

| Projeto | Pasta | Comando |
|---|---|---|
| Nginx (NPM) | `multiplica-nginx` | `docker compose up -d` |
| SSD | `multiplica-ssd` | `docker compose up -d` (exige `.env` com `PROXY_NET=proxy`) |
| **PIQ** | `multiplica-piq` | `sops exec-env segredos.enc.env 'docker compose up -d'` |

- **Só o PIQ precisa do `sops exec-env`.** `docker compose up -d` puro no PIQ recria o container com as
  variáveis vazias e ele deixa de funcionar. `restart` e `stop` não têm esse problema.
- **Ordem do zero:** Nginx primeiro (ele cria a rede `proxy`), depois SSD e PIQ.
- A chave privada do servidor precisa estar em `~/.config/sops/age/keys.txt` (já está).

| Para | Comando |
|---|---|
| Ver o estado | `docker ps` |
| Ver logs | `docker logs -f piq-api` (ou `piq-web`, `rodrigo-site`, `npm`) |
| Reiniciar sem mexer em variáveis | `docker compose restart` |
| Parar | `docker compose stop` |
| Atualizar código do PIQ (`git pull`) | `sops exec-env segredos.enc.env 'docker compose up -d --build'` |
| Atualizar só os segredos do PIQ (`git pull`) | `sops exec-env segredos.enc.env 'docker compose up -d'` |
| Checar saúde (pelo domínio) | `curl https://piq.multiplicaservidor.com.br/saude/banco` |

Containers: `npm` (porta de entrada, HTTPS), `rodrigo-site` (site do SSD), `piq-web` (telas e proxy da
API) e `piq-api` (regras, banco e e-mail). Todos se falam pela rede Docker `proxy`.

### Banco de dados

O PIQ usa o Supabase de **sa-east-1** (Session pooler, porta 5432) na `DATABASE_URL`. O
`DATABASE_URL_ANTIGA` do arquivo de segredos é o banco dos EUA, mantido só para reverter; o container
**não** a recebe (o compose lista as variáveis uma a uma). Para reverter, troque o valor da
`DATABASE_URL` pelo da antiga e suba de novo. Plano da migração em
[`plans/migracao-supabase-brasil.plan.md`](plans/migracao-supabase-brasil.plan.md).

### Convenção para os outros projetos

- Um `segredos.enc.env` **por repositório**, sempre com esse nome, e uma cópia do `.sops.yaml`
  com as mesmas chaves públicas. Um par de chaves protege todos os projetos.
- Mesmo comando de subida em todos: `sops exec-env segredos.enc.env 'docker compose up -d'`.
- Não usar repositório central de segredos: subir um projeto não pode depender de outro.
- Alguém externo que precise de um projeto só: crie uma chave para essa pessoa e inclua-a **apenas**
  no `.sops.yaml` daquele projeto.
- Projetos sem segredo (ex.: SSD, cujo único valor é o nome da rede) não precisam do arquivo.
