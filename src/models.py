"""
src/models.py
─────────────────────────────────────────────────────────────────────────────
Modelos de dados do projeto epanet-g23.

Toda a lógica de leitura (reader.py) e escrita (inp_writer.py) opera sobre
essas estruturas — elas são o contrato entre as duas fases do pipeline.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


def _r(v: float | None, n: int = 4) -> float | None:
    return round(v, n) if v is not None else None


# ══════════════════════════════════════════════════════════════════════════════
#  METADADOS DA REDE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NetworkMetadata:
    """
    Parâmetros globais extraídos do cabeçalho da planilha CORSAN
    e do arquivo de configuração do projeto.
    """
    projeto_nome: str                   # Ex: "Gravataí Parada 96"
    fonte_coordenadas: str              # Nome do arquivo CSV
    fonte_dimensionamento: str          # Nome do arquivo XLSX
    aba_dimensionamento: str            # Nome da aba lida

    # Parâmetros hidráulicos globais
    N_economias: float | None = None    # Número total de economias (lotes)
    C_HW: float | None = None           # Coef. rugosidade Hazen-Williams (adim.)
    Q_unit_ls: float | None = None      # Vazão unitária por economia (l/s)
    pressao_PT_mca: float | None = None # Pressão no Ponto de Tomada (mca)

    reservoir_id: str = "PT"            # ID do nó reservatório/ponto de tomada

    def to_dict(self) -> dict:
        return {
            "projeto_nome":          self.projeto_nome,
            "fonte_coordenadas":     self.fonte_coordenadas,
            "fonte_dimensionamento": self.fonte_dimensionamento,
            "aba_dimensionamento":   self.aba_dimensionamento,
            "N_economias":           _r(self.N_economias),
            "C_HW":                  _r(self.C_HW),
            "Q_unit_ls":             _r(self.Q_unit_ls),
            "pressao_PT_mca":        _r(self.pressao_PT_mca),
            "reservoir_id":          self.reservoir_id,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  NÓ (JUNCTION / RESERVOIR)
# ══════════════════════════════════════════════════════════════════════════════

NodeType = Literal["junction", "reservoir"]


@dataclass
class Node:
    """
    Representa um nó da rede — junction ou reservoir.

    Elevação:
        elevation_m é a cota do terreno no nó.
        Para reservatórios, total_head_m é o nível piezométrico
        (cota + pressão) e é o valor usado no EPANET [RESERVOIRS].

    Demanda:
        base_demand_ls = n_contrib × Q_unit_ls
        Calculada no reader; zero para reservatórios.

    Coordenadas:
        Em sistema métrico projetado (UTM ou similar).
        None quando o nó não foi encontrado no CSV.
    """
    id: str
    type: NodeType

    # Posição geográfica (do CSV)
    easting: float | None = None
    northing: float | None = None

    # Hidráulica (da planilha)
    elevation_m: float | None = None         # Cota do terreno (m)
    pressao_disp_mca: float | None = None    # Pressão disponível (mca)
    pressao_est_mca: float | None = None     # Pressão estática (mca)
    nivel_piezo_m: float | None = None       # Nível piezométrico (m)

    # Demanda
    n_contrib: float | None = None           # Economias acumuladas no nó
    base_demand_ls: float = 0.0             # Demanda base (l/s)

    # Exclusivo para reservatório
    total_head_m: float | None = None        # Carga total = nivel_piezo_m

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "type":             self.type,
            "easting":          _r(self.easting),
            "northing":         _r(self.northing),
            "elevation_m":      _r(self.elevation_m),
            "pressao_disp_mca": _r(self.pressao_disp_mca),
            "pressao_est_mca":  _r(self.pressao_est_mca),
            "nivel_piezo_m":    _r(self.nivel_piezo_m),
            "n_contrib":        _r(self.n_contrib),
            "base_demand_ls":   _r(self.base_demand_ls),
            "total_head_m":     _r(self.total_head_m),
        }

    def is_reservoir(self) -> bool:
        return self.type == "reservoir"

    def is_junction(self) -> bool:
        return self.type == "junction"

    def has_coordinates(self) -> bool:
        return self.easting is not None and self.northing is not None


# ══════════════════════════════════════════════════════════════════════════════
#  TRECHO (PIPE)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Pipe:
    """
    Representa um trecho (pipe) da rede.

    Identificação:
        id segue o padrão P_<node1>_<node2>.
        Duplicatas (trechos paralelos) recebem sufixo _2, _3...

    Rugosidade:
        rugosidade_HW é o coeficiente C de Hazen-Williams (adimensional).
        Valor padrão extraído dos metadados da planilha (tipicamente 150).

    Campos de dimensionamento:
        Armazenados para rastreabilidade e para o relatório de verificação.
        O gerador INP usa apenas: id, node1, node2, comprimento_m,
        diametro_mm, rugosidade_HW.
    """
    id: str
    node1: str                              # ID do nó montante
    node2: str                              # ID do nó jusante

    # Geometria
    comprimento_m: float | None = None      # Comprimento (m)
    diametro_mm: float | None = None        # Diâmetro nominal (mm)
    rugosidade_HW: float = 150.0            # Coef. Hazen-Williams (adim.)

    # Economias
    ni_trecho: float | None = None          # Economias no trecho
    n_contrib_montante: float | None = None # N acumulado montante
    n_contrib_jusante: float | None = None  # N acumulado jusante

    # Resultados hidráulicos (da planilha — para rastreabilidade)
    vazao_ls: float | None = None
    vazao_m3s: float | None = None
    velocidade_ms: float | None = None
    perda_unit_mKm: float | None = None
    perda_total_m: float | None = None

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "node1":               self.node1,
            "node2":               self.node2,
            "comprimento_m":       _r(self.comprimento_m),
            "diametro_mm":         _r(self.diametro_mm),
            "rugosidade_HW":       _r(self.rugosidade_HW),
            "ni_trecho":           _r(self.ni_trecho),
            "n_contrib_montante":  _r(self.n_contrib_montante),
            "n_contrib_jusante":   _r(self.n_contrib_jusante),
            "vazao_ls":            _r(self.vazao_ls),
            "vazao_m3s":           _r(self.vazao_m3s),
            "velocidade_ms":       _r(self.velocidade_ms),
            "perda_unit_mKm":      _r(self.perda_unit_mKm),
            "perda_total_m":       _r(self.perda_total_m),
        }

    def is_zero_flow(self) -> bool:
        """Trecho sem vazão (ramal sem demanda a jusante)."""
        return self.vazao_ls is not None and self.vazao_ls == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  REDE (CONTAINER PRINCIPAL)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Network:
    """
    Container principal — representa a rede completa.

    Métodos utilitários facilitam o acesso por ID sem percorrer as listas
    a cada chamada.
    """
    metadata: NetworkMetadata
    nodes: list[Node] = field(default_factory=list)
    pipes: list[Pipe] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "nodes":    [n.to_dict() for n in self.nodes],
            "pipes":    [p.to_dict() for p in self.pipes],
        }

    # ── índices construídos sob demanda ──────────────────────────────────────
    _node_index: dict[str, Node] = field(default_factory=dict, init=False, repr=False)
    _pipe_index: dict[str, Pipe] = field(default_factory=dict, init=False, repr=False)

    def build_indexes(self) -> None:
        """Constrói índices por ID para acesso O(1). Chamar após popular nodes/pipes."""
        self._node_index = {n.id: n for n in self.nodes}
        self._pipe_index = {p.id: p for p in self.pipes}

    def get_node(self, node_id: str) -> Node | None:
        return self._node_index.get(node_id)

    def get_pipe(self, pipe_id: str) -> Pipe | None:
        return self._pipe_index.get(pipe_id)

    # ── filtros úteis ─────────────────────────────────────────────────────────
    @property
    def junctions(self) -> list[Node]:
        return [n for n in self.nodes if n.is_junction()]

    @property
    def reservoirs(self) -> list[Node]:
        return [n for n in self.nodes if n.is_reservoir()]

    @property
    def nodes_with_coordinates(self) -> list[Node]:
        return [n for n in self.nodes if n.has_coordinates()]

    @property
    def active_pipes(self) -> list[Pipe]:
        """Trechos com vazão > 0."""
        return [p for p in self.pipes if not p.is_zero_flow()]

    # ── validação rápida ──────────────────────────────────────────────────────
    def validate(self) -> list[str]:
        """
        Retorna lista de mensagens de problema encontrados.
        Lista vazia = rede consistente.
        """
        issues: list[str] = []
        self.build_indexes()
        node_ids = set(self._node_index)

        for pipe in self.pipes:
            if pipe.node1 not in node_ids:
                issues.append(f"Trecho '{pipe.id}': node1 '{pipe.node1}' não existe em nodes.")
            if pipe.node2 not in node_ids:
                issues.append(f"Trecho '{pipe.id}': node2 '{pipe.node2}' não existe em nodes.")
            if pipe.diametro_mm is None:
                issues.append(f"Trecho '{pipe.id}': diâmetro ausente.")
            if pipe.comprimento_m is None:
                issues.append(f"Trecho '{pipe.id}': comprimento ausente.")

        for node in self.nodes:
            if node.elevation_m is None:
                issues.append(f"Nó '{node.id}': elevação ausente.")
            if not node.has_coordinates():
                issues.append(f"Nó '{node.id}': coordenadas ausentes.")

        if not self.reservoirs:
            issues.append("Nenhum nó do tipo 'reservoir' encontrado.")

        return issues

    def summary(self) -> str:
        return (
            f"Rede: {self.metadata.projeto_nome}\n"
            f"  Nós       : {len(self.nodes)} "
            f"({len(self.junctions)} junctions, {len(self.reservoirs)} reservoirs)\n"
            f"  Trechos   : {len(self.pipes)} "
            f"({len(self.active_pipes)} com vazão > 0)\n"
            f"  C_HW      : {self.metadata.C_HW}\n"
            f"  Q_unit    : {self.metadata.Q_unit_ls} l/s\n"
            f"  Pressão PT: {self.metadata.pressao_PT_mca} mca"
        )
