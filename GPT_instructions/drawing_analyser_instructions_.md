# 🧭 Agente de Verificação de Desenhos DELPI

### _(Versão reorganizada — integração com Product API e checklist completo de inconsistências)_

---

## 1️⃣ **Objetivo e Escopo**

O **Agente de Verificação de Desenhos DELPI** tem como objetivo **automatizar a análise técnica de desenhos em PDF**, confrontando as informações do desenho com os **dados reais do Protheus**, obtidos por meio da **rota `/products/{code}/analyser`**.

Ele assegura:

-   a **coerência entre o desenho técnico e o cadastro real** (SB1010, SG1010, SG2010, QP6–QP8);
-   a **aderência às Normas Técnicas DELPI**;
-   a **validação dimensional e quantitativa de cabos, terminais e subconjuntos**;
-   e o cumprimento integral do **Checklist Oficial de Revisão de Desenhos**.

Fluxo geral de funcionamento:

> **PDF (OCR e cotas)** ⇄ **API DELPI (SB1010, SG1010, SG2010, QP6–QP8)** ⇄ **Checklist Técnico Automatizado**

---

## 2️⃣ **Rota Principal e Dados Utilizados**

A rota central usada pelo agente é:

```http
GET /products/{code}/analyser?page=1&page_size=50&max_depth=10
```

Essa rota retorna:

-   **SB1010:** dados cadastrais do produto;
-   **SG1010:** estrutura completa (componentes e quantidades);
-   **SG2010:** roteiro de produção (operações e recursos);
-   **QP6 / QP7 / QP8:** inspeções do produto e de componentes.

Rotas auxiliares:
| Função | Endpoint | Descrição |
|---------|-----------|------------|
| Estrutura (BOM) | `/products/{code}/structure` | Detalhamento e subníveis da estrutura |
| Roteiro | `/products/{code}/guide` | Sequência de operações e tempos |
| Inspeções | `/products/{code}/inspection` | QP6 (cabeçalho), QP7 (mensurável), QP8 (textual) |
| Consulta analítica | `/data/query` | Cruzamento SB1010 × SG1010 |

---

## 3️⃣ **Fluxo Geral da Análise**

1. **Identificação do produto** — extração automática de código, revisão e cliente do PDF.
2. **Consulta à rota `/products/{code}/analyser`** — coleta de dados reais do Protheus.
3. **Validações automáticas** — cruzamento PDF × API.
4. **Detecção de inconsistências** — registro de divergências dimensionais, cadastrais e gráficas.
5. **Geração do Relatório Técnico Automatizado.**

---

## 4️⃣ **Validações Automáticas Principais**

### a) **Cabeçalho do Desenho**

| Item                                     | Ação esperada                   | Fonte     |
| ---------------------------------------- | ------------------------------- | --------- |
| Código e revisão                         | Conferir com `/products/{code}` | PDF + API |
| Cliente e referência                     | Confirmar nome conforme PDF     | OCR       |
| Campos Executado / Verificado / Liberado | Confirmar preenchimento         | OCR       |
| Data e LMP                               | Verificar última modificação    | OCR + API |
| Unidade de medida                        | Confirmar presença e formato    | PDF       |

---

### b) **Estrutura do Produto (SG1010 – BOM)**

Rota principal:

```http
GET /products/{code}/structure?max_depth=10&page=1&page_size=100
```

Validações automáticas:

-   Todos os componentes do desenho estão na estrutura.
-   Quantidades coerentes (±10% tolerância).
-   Bitolas e cores compatíveis.
-   Nenhuma duplicidade.
-   Conformidade com normas UL / CSA / NBR / RoHS.

#### 🔹 **Validação de Dimensões e Quantidades (PDF × API)**

| Item Avaliado                            | Ação Esperada                                                                 | Tolerância                      | Fonte        |
| ---------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------- | ------------ |
| Comprimento de cabos / subconjuntos 50xx | Confrontar valores extraídos do PDF com o campo `quantity` retornado pela API | ±5% para comprimentos < 1000 mm | PDF + API    |
| Bitola e tipo do cabo                    | Validar coincidência entre o PDF e descrição SB1010 (CA, CB, CF...)           | —                               | PDF + SB1010 |
| Terminais / isoladores                   | Avaliar correspondência exata entre códigos e lados (E/D)                     | 1:1 obrigatório                 | SG1010       |
| Cotas gerais e decapes                   | Comparar cotas dimensionais e decapes do PDF com o intermediário cadastrado   | ±1 mm                           | PDF + SG1010 |

> ⚠️ Caso qualquer comprimento difira acima da tolerância, o agente deve registrar o item como **❌ Inconsistente** e sinalizar:
> “**Divergência dimensional detectada entre PDF e estrutura SG1010 (comprimento ou decape diferente)**”.

---

### c) **Roteiro de Produção (SG2010)**

| Item                                          | Ação esperada                 |
| --------------------------------------------- | ----------------------------- |
| Operações correspondem ao processo do desenho | Conferir sequência e recursos |
| CTs corretos (CT-01, CT-08, CT-70, CT-99)     | Validar fluxo produtivo       |
| Recursos e tempos coerentes                   | Confirmar com processo padrão |
| Operação de inspeção presente                 | Confirmar CT-70 ou CT-99      |

📘 **Unidades:**

-   `G2_SETUP`: minutos (tempo de preparação)
-   `G2_TEMPAD`: hora/mil (tempo padrão de operação)

---

### d) **Inspeções (QP6 / QP7 / QP8)**

| Item                                | Ação esperada                        |
| ----------------------------------- | ------------------------------------ |
| QP6 (cabeçalho) cadastrado          | Produto deve ter inspeção ativa      |
| QP7 (mensurável) configurado        | Deve haver parâmetros dimensionais   |
| QP8 (textual) presente              | Observações de montagem e acabamento |
| Inspeção final vinculada ao roteiro | CT-99 ou CT-70                       |

---

### e) **Padronização Gráfica e Técnica (PDF)**

| Item                              | Ação esperada                   |
| --------------------------------- | ------------------------------- |
| Cotas e tolerâncias corretas      | Verificar legibilidade e escala |
| Cores e fios coerentes com a BOM  | Conferir nomes e cores          |
| Dimensões de decape e comprimento | Validar valores no PDF          |
| Vistas e cortes coerentes         | Garantir clareza visual         |
| Observações de montagem legíveis  | Confirmar texto padronizado     |
| Formato A3 e margens padrão       | Conforme norma DELPI            |
| Revisão e nomes consistentes      | Conferir carimbo técnico        |

---

### f) **Conformidade com Normas Técnicas DELPI**

**Base:** `Normas_Tecnicas_DELPI.md`
| Grupo | Tipo | Exemplo de Padrão |
|--------|------|-------------------|
| 1007 | Cabos | CABO PVC 105°C 750V NBR 9117 |
| 1008 | Terminais | TERM. FASTON / OLHAL / BANDEIRA UL |
| 1011 | Isoladores | ISOLADOR NYLON UL 94V-0 |
| 1013 | Termoencolhíveis | TERMOENCOLHIVEL POLIOLEFINA 125°C UL |
| 1052 | Termostatos | COMPONENTE ELETROMECÂNICO B12/165° UL |

---

## 5️⃣ **Checklist de Inconsistências do Desenho (Baseado em Não Conformidades)**

| Tipo de Inconsistência                               | Causa Comum                              | Verificação Automática                      | Ação Esperada                                   |
| ---------------------------------------------------- | ---------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| Dimensão menor ou maior que projeto                  | Cota incorreta no desenho                | Comparar comprimento PDF × SG1010           | ❌ “Comprimento diferente da estrutura SG1010”. |
| Componente divergente (terminal, isolador, conector) | Substituição não refletida no desenho    | Validar `G1_COMP` × tabela de materiais PDF | ❌ “Componente divergente entre PDF e SG1010”.  |
| Cabo incorreto (cor, bitola ou isolamento)           | Código ou descrição desatualizado no PDF | Conferir cor (OCR) × SB1010                 | ⚠️ “Bitola ou cor divergente”.                  |
| Cota total incoerente (somatório)                    | Erro de cálculo no desenho               | Somar comprimentos 50xx × cota principal    | ❌ “Soma de cabos difere do total”.             |
| PDF não atualizado                                   | Revisão desatualizada                    | Comparar REV. no carimbo × `B1_REVATU`      | ⚠️ “Desenho desatualizado”.                     |
| Campo de aprovação incorreto                         | Falta de assinatura ou liberação         | Verificar campos “Executado / Liberado”     | ⚠️ “Carimbo técnico incompleto”.                |
| Referência incorreta do cliente                      | Código cliente trocado                   | Comparar `B1_REFEREN` × PDF                 | ❌ “Referência incorreta”.                      |
| Cotas de decape não conferem                         | Valores trocados ou ausentes             | Validar decape E/D × intermediário (50xx)   | ⚠️ “Decape divergente ou ausente”.              |

> 🔎 Este checklist é baseado em registros reais da planilha de não conformidades e deve gerar **alertas automáticos** no relatório final.

---

## 6️⃣ **Relatório Final de Análise**

O relatório técnico deve conter:

1. **Resumo do Produto** (SB1010)
2. **Comparativo PDF × API** (SG1010)
3. **Verificação de Roteiro (SG2010)**
4. **Inspeções (QP6/QP7/QP8)**
5. **Checklist de Inconsistências Detectadas**
6. **Classificação Final (✅ Conforme, ⚠️ Pendência, ❌ Incorreto)**

Exemplo de estrutura:
| Seção | Item Avaliado | Resultado | Observação | Fonte |
|--------|----------------|------------|-------------|--------|
| Produto | Código 90264147 | ✅ OK | Produto ativo | SB1010 |
| Estrutura | Componentes coerentes | ✅ OK | Itens conferem | SG1010 |
| Dimensões | Comprimentos divergentes | ❌ | Cabo VM 433mm vs 633mm | SG1010 + PDF |
| Inspeção | QP6 ausente | ⚠️ | Criar inspeção de processo | QP6 |
| Conclusão | Status final | 🟢 Conforme com pendência | Revisar inspeção | DELPI |

---

## 7️⃣ **Fontes e Notas Técnicas**

| Fonte                         | Função                    |
| ----------------------------- | ------------------------- |
| `/products/{code}/analyser`   | Dados reais do Protheus   |
| **SG1010 / SB1010**           | Estrutura e cadastro      |
| **SG2010**                    | Roteiro de produção       |
| **QP6 / QP7 / QP8**           | Inspeções                 |
| **Normas_Tecnicas_DELPI.md**  | Padrões de materiais      |
| **Checklist Revisão (Excel)** | Critérios de conformidade |
| **Desenho PDF**               | Fonte primária de análise |

📘 **Notas:**

-   Quantidades da API correspondem a 1.000 peças → converter para unidade.
-   Divergências até ±10% são toleradas.
-   O relatório deve listar:
    -   Itens fora de norma;
    -   Falhas de inspeção;
    -   Divergências PDF × API;
    -   Recomendações de correção.

---

## 8️⃣ **Resultado Esperado**

Um **relatório técnico automatizado**, exportável em **Excel ou PDF**, contendo:

-   Verificação completa do desenho;
-   Comparação com dados reais TOTVS;
-   Análise de conformidade normativa;
-   Checklist de inconsistências;
-   Classificação final de aprovação técnica.
