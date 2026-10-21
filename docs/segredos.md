# Segredos (SOPS + age)

Os segredos do PIQ ficam em `segredos.enc.env`, **criptografados e versionados**. Os nomes das
variáveis aparecem; os valores não. Não existe `.env` no servidor. O modelo com a explicação de
cada variável continua em `.env.example`.

## Chaves

| Chave | Onde fica | Para quê |
|---|---|---|
| privada do **servidor** | `~/.config/sops/age/keys.txt` no servidor | subir o projeto |
| privada **pessoal** | `~/.config/sops/age/keys.txt` no Mac **e no gerenciador de senhas** | editar segredos e recuperar |
| públicas (as duas) | `.sops.yaml` | criptografar. Não são segredo |

**A chave privada é a única coisa a proteger.** Perdendo as duas, o `segredos.enc.env` é
irrecuperável e todo valor precisa ser gerado de novo. Mantenha cópia fora do servidor.

## Dia a dia

```bash
sops segredos.enc.env        # abre editor, criptografa ao salvar (Mac)
git add segredos.enc.env && git commit && git push
```

No servidor, sem deixar `.env` no disco:

```bash
cd ~/workspace/multiplica-piq && git pull
sops exec-env segredos.enc.env 'docker compose up -d --build'
```

O compose repassa as variáveis ao container (`environment:`). Rodar `docker compose up` **sem**
o `sops exec-env` recria o container com variáveis vazias. `docker compose restart` é seguro.

## Servidor novo (recuperação)

```bash
git clone git@github.com:virtus-id/multiplica-piq.git ~/workspace/multiplica-piq
mkdir -p ~/.config/sops/age && chmod 700 ~/.config/sops/age
# colar a chave privada pessoal (do gerenciador de senhas) em ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
cd ~/workspace/multiplica-piq && sops exec-env segredos.enc.env 'docker compose up -d --build'
```

Para o servidor novo ter a própria chave: `age-keygen -o ~/.config/sops/age/keys.txt`, troque
a pública antiga em `.sops.yaml` pela nova e rode `sops updatekeys segredos.enc.env`.

## Instalar as ferramentas

- Mac: `brew install sops age`. O SOPS procura a chave em `~/Library/Application Support/sops/age/keys.txt`;
  aponte para ela com `ln -s ~/.config/sops/age/keys.txt "$HOME/Library/Application Support/sops/age/keys.txt"`.
- Ubuntu: `apt install age` e baixar o binário do SOPS em github.com/getsops/sops/releases.

## Se uma chave vazar

Troque a chave (`sops updatekeys`) **e** os valores que ela abria (senha do banco, SMTP,
segredos). O histórico do git guarda as versões antigas, então só trocar a chave não basta.
