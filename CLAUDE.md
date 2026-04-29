# epanet-g23 — Contexto do Projeto

## Objetivo

Ferramenta Python para gerar arquivos `.INP` do EPANET a partir de duas fontes de dados:

1. **CSV de coordenadas** — campos: `Name | Easting | Northing`
2. **XLSX de dimensionamento** — planilha de cálculo de rede de água no padrão CORSAN (RS)

O pipeline tem duas fases independentes:

```
[CSV + XLSX] ──(src/reader.py)──► [JSON: rede_agua.json] ──(src/inp_writer.py)──► [.INP EPANET]
```

---

## Contexto de negócio

- **Empresa:** G23 Projetos de Engenharia e Consultoria Ltda. (G23 Engenharia)
- **Proprietário:** Engenheiro Civil Gabriel
- **Uso:** Projetos de abastecimento de água para loteamentos — clientes como CORSAN (RS)
- **Reutilização:** A planilha CORSAN tem layout fixo entre projetos. Parâmetros por projeto
  (paths, linha de início de dados, aba) ficam em `config/<nome_rede>.yaml`.

---

## Estrutura da Planilha CORSAN (XLSX)

### Metadados — cabeçalho fixo

| Campo           | Célula (padrão) | Descrição                          |
|-----------------|-----------------|------------------------------------|
| N_economias     | M5              | Número de economias (lotes)        |
| C_HW            | M6              | Coef. rugosidade Hazen-Williams    |
| Q_unit_ls       | M7              | Vazão unitária (l/s/economia)      |
| pressao_PT_mca  | M8              | Pressão no Ponto de Tomada (mca)   |

> Células podem variar por versão da planilha — ajustar em `config/<rede>.yaml`.

### Dados de trechos — a partir da linha 13

Cada linha = um trecho (pipe). Mapeamento de colunas (1-based):

| Coluna | Campo                  | Descrição                               |
|--------|------------------------|-----------------------------------------|
| A (1)  | montante               | ID do nó montante                       |
| B (2)  | jusante                | ID do nó jusante                        |
| C (3)  | ni_trecho              | Nº de economias no trecho               |
| D (4)  | diametro_mm            | Diâmetro nominal (mm)                   |
| E (5)  | comprimento_m          | Comprimento (m)                         |
| F (6)  | n_contrib_montante     | N acumulado no nó montante              |
| G (7)  | n_contrib_jusante      | N acumulado no nó jusante               |
| H (8)  | vazao_ls               | Vazão (l/s)                             |
| I (9)  | vazao_m3s              | Vazão (m³/s)                            |
| J (10) | velocidade_ms          | Velocidade (m/s)                        |
| K (11) | perda_unit_mKm         | Perda de carga unitária (m/km)          |
| L (12) | perda_total_m          | Perda de carga total (m)                |
| M (13) | cota_montante          | Cota do terreno montante (m)            |
| N (14) | cota_jusante           | Cota do terreno jusante (m)             |
| O (15) | desnivel_terreno       | Desníveldo terreno (m)                  |
| P (16) | pressao_disp_mont      | Pressão disponível montante (mca)       |
| Q (17) | pressao_disp_jus       | Pressão disponível jusante (mca)        |
| R (18) | pressao_est_mont       | Pressão estática montante (mca)         |
| S (19) | pressao_est_jus        | Pressão estática jusante (mca)          |
| T (20) | nivel_piezo_mont       | Nível piezométrico montante (m)         |
| U (21) | nivel_piezo_jus        | Nível piezométrico jusante (m)          |

> Leitura termina na primeira linha com célula vazia na coluna A.

---

## Modelos de dados (`src/models.py`)

```
Network
├── metadata: NetworkMetadata
├── nodes: list[Node]
│   ├── type = "junction"   → vai para [JUNCTIONS] no INP
│   └── type = "reservoir"  → vai para [RESERVOIRS] no INP
└── pipes: list[Pipe]       → vai para [PIPES] no INP
```

### Nó reservatório

- ID padrão: `"PT"` (Ponto de Tomada)
- `total_head_m = nivel_piezo_mont` do primeiro trecho onde PT é montante
- No EPANET, HEAD do reservatório = nível piezométrico (cota + pressão)

### Demanda base dos nós

```
base_demand_ls = n_contrib × Q_unit_ls
```

- `n_contrib` vem da coluna G (n_contrib_jusante) quando o nó aparece como jusante
- Para o nó PT (reservatório): `base_demand_ls = 0`
- **Nunca inferir demanda por outro método** sem validação explícita com o engenheiro

### Elevação dos nós

- Quando o nó aparece como **montante**: usa `cota_montante`
- Quando aparece **apenas como jusante**: usa `cota_jusante`
- Primeira ocorrência prevalece; divergências > 0.01 m geram aviso (não erro)

---

## Gerador INP (`src/inp_writer.py`)

### Seções implementadas

| Seção EPANET    | Fonte                          |
|-----------------|--------------------------------|
| `[TITLE]`       | metadata.projeto_nome          |
| `[JUNCTIONS]`   | nodes onde type == "junction"  |
| `[RESERVOIRS]`  | nodes onde type == "reservoir" |
| `[PIPES]`       | pipes                          |
| `[COORDINATES]` | nodes com easting/northing     |
| `[OPTIONS]`     | valores padrão EPANET          |
| `[TIMES]`       | valores padrão (análise estática: Duration 0) |
| `[REPORT]`      | valores padrão                 |

### Unidades EPANET

O arquivo `.INP` usa **LPS** (litros por segundo) como unidade de fluxo.
Isso implica:
- Vazão → l/s  ✔ (já está na estrutura)
- Pressão → metros  ✔
- Comprimento → metros  ✔
- Diâmetro → **milímetros** no INP (campo `Diameter` em [PIPES] é em mm para LPS)

### Fórmula de perda de carga

Hazen-Williams — especificar `Headloss H-W` em `[OPTIONS]`.

---

## Convenções de código

- **Python 3.11+**, tipagem completa com `from __future__ import annotations`
- Dataclasses para modelos (`@dataclass`, sem herança desnecessária)
- Nenhuma dependência além de `openpyxl` (Fase 1) — stdlib para o resto
- Separador decimal: vírgula no Excel → sempre converter com `.replace(",", ".")`
- Encoding CSV: `utf-8-sig` (BOM do Excel)
- IDs de nós são sempre `str` — nunca `int`, mesmo que pareçam numéricos
- IDs de trechos: padrão `P_<node1>_<node2>`; duplicatas recebem sufixo `_2`, `_3`...
- Todos os valores numéricos ausentes → `None` (não `0`, não `""`)
- Float com 4 casas no JSON; 3 casas no INP (formato EPANET)

---

## Configuração por projeto (`config/<rede>.yaml`)

```yaml
projeto_nome: "Gravataí Parada 96"
csv_path: "data/gravatai_p96/coordenadas.csv"
xlsx_path: "data/gravatai_p96/dimensionamento.xlsx"
sheet_name: null          # null = primeira aba
data_start_row: 13
reservoir_id: "PT"
output_json: "data/gravatai_p96/rede_agua.json"
output_inp: "output/gravatai_p96/gravatai_p96.inp"
meta_cells:
  N_economias:    [5, 13]
  C_HW:           [6, 13]
  Q_unit_ls:      [7, 13]
  pressao_PT_mca: [8, 13]
```

---

## O que NÃO fazer

- Não usar `pandas` — `openpyxl` direto para preservar controle sobre células mescladas
- Não converter IDs de nós para inteiro — nó `"PT"` e nó `"13"` são strings
- Não assumir que `n_contrib_jusante == 0` significa nó terminal — verificar topologia
- Não alterar o `COL_MAP` global — ajustes de layout vão no `config/<rede>.yaml`
- Não gerar seções `[PATTERNS]`, `[CURVES]`, `[CONTROLS]` — fora do escopo atual
- Não rodar simulação EPANET programaticamente — validação é manual no EPANET GUI

---

## Referências

- EPANET 2.2 Input File Format: https://epanet22.readthedocs.io/en/latest/back_matter.html
- Hazen-Williams no EPANET: unidades LPS, diâmetro em mm, C adimensional
