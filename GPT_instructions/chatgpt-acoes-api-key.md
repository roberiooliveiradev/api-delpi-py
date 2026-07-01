# Custom GPT — Actions api-delpi-py

**URL produção:** `https://api.transformamaisdelpi.com.br`

---

## Token fixo (recomendado para o agente)

Não é necessário chamar `POST /system/login` no Custom GPT.

1. No servidor, gere e configure em `.env`:

```bash
openssl rand -hex 32
```

```env
GPT_API_TOKEN=cole_o_token_aqui
```

2. Recrie o container:

```bash
docker compose up -d --force-recreate api
```

3. No builder do GPT → **Actions** → Autenticação:

| Campo | Valor |
|-------|--------|
| Tipo | Chave API / Bearer |
| Header | `Authorization` |
| Valor | `Bearer <GPT_API_TOKEN>` |

Alternativa equivalente: header `X-Api-Key` com o mesmo valor.

4. Teste:

```bash
curl -s -H "Authorization: Bearer SEU_GPT_API_TOKEN" \
  "https://api.transformamaisdelpi.com.br/products/search/description?q=chicote&limit=1"
```

Sem token → `401`. Com token → `200`.

---

## Login JWT (uso humano / scripts)

`POST /system/login` com credenciais `DB_USER` / `DB_PASSWORD` continua disponível para renovação manual de JWT (~1 ano).

O agente GPT deve usar **`GPT_API_TOKEN`**, não credenciais do banco.

---

## Segurança

- Não commitar `.env`.
- Rotacionar `GPT_API_TOKEN` se vazar — atualizar `.env` e a Action no ChatGPT.
- `JWT_SECRET` separado do token GPT.
