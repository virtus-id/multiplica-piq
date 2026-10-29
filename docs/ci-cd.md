# CI/CD — feature → Pull Request → main → deploy

```text
branch feat/… ──PR──► check "validate" (Validate SDD) ──merge──► main ──push──► Deploy (GitHub Actions) ──ssh──► servidor
```

- **Desenvolvimento** só em branch de feature. A `main` não aceita push direto.
- **Pull Request** roda `Validate SDD` (`.github/workflows/sdd-validate.yml`), check obrigatório para o merge.
- **Merge na main** dispara `Deploy` (`.github/workflows/deploy.yml`): entra no servidor por SSH, faz
  `git merge --ff-only` até o commit do merge e roda `sops exec-env segredos.enc.env 'docker compose up -d --build'`
  (o mesmo procedimento do README). Falha se o servidor divergir ou se `piq-api` não ficar `healthy`.
- Deploys não rodam em paralelo (`concurrency: deploy-producao`). Não há migração automática.

## Secrets (Settings → Secrets and variables → Actions → Repository secrets)

| Secret | Conteúdo |
|---|---|
| `DEPLOY_HOST` | endereço do servidor (o `HostName` do alias `multiplica` no `~/.ssh/config`) |
| `DEPLOY_USER` | usuário SSH do servidor (o `User` do mesmo alias) |
| `DEPLOY_SSH_KEY` | chave PRIVADA de uma chave SSH **só do deploy** (ed25519), nunca a pessoal |
| `PIQ_SLACK_WEBHOOK_URL` | (opcional) Incoming Webhook do Slack que recebe o resultado de cada deploy; sem ele o aviso é pulado |
| `DEPLOY_KNOWN_HOSTS` | saída de `ssh-keyscan -t ed25519 <host>`, conferida com o fingerprint do servidor |

Gerar a chave e autorizá-la no servidor:

```bash
ssh-keygen -t ed25519 -N "" -C "github-actions-deploy" -f ./deploy_key
ssh-copy-id -i ./deploy_key.pub multiplica         # ou colar a .pub em ~/.ssh/authorized_keys do servidor
gh secret set DEPLOY_SSH_KEY < ./deploy_key && rm ./deploy_key ./deploy_key.pub
gh secret set DEPLOY_HOST --body "<host>" && gh secret set DEPLOY_USER --body "<usuário>"
ssh-keyscan -t ed25519 <host> | gh secret set DEPLOY_KNOWN_HOSTS   # confira o fingerprint antes
```

Recomendado depois: prefixar a linha da chave em `authorized_keys` com `restrict,` para reduzir o que ela pode fazer.

## Proteção da `main` (aplicada via API do GitHub)

PR obrigatório (0 aprovações: repositório de uma pessoa), check `validate` obrigatório e atualizado com a `main`,
sem force push, sem exclusão da branch, valendo também para administradores.
