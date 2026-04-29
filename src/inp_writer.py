"""
src/inp_writer.py
─────────────────────────────────────────────────────────────────────────────
Gera arquivo .INP do EPANET 2.2 a partir de um objeto Network.

Unidades: LPS (litros por segundo)
  - Vazão      → l/s
  - Pressão    → metros
  - Comprimento→ metros
  - Diâmetro   → milímetros
  - Fórmula    → Hazen-Williams

Uso:
    python -m src.inp_writer config/gravatai_p96.yaml
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.models import Network
from src.reader import build_network, load_config


def _f(v: float | None, decimals: int = 3) -> str:
    """Formata float para INP; None vira zero."""
    return f"{v:.{decimals}f}" if v is not None else f"{0:.{decimals}f}"


def write_inp(network: Network, out_path: Path) -> None:
    lines: list[str] = []

    # [TITLE]
    lines += [
        "[TITLE]",
        network.metadata.projeto_nome,
    ]

    # [JUNCTIONS]
    lines += [
        "\n[JUNCTIONS]",
        ";ID                 Elev        Demand      Pattern",
    ]
    for node in network.junctions:
        lines.append(
            f" {node.id:<20}{_f(node.elevation_m):<12}{_f(node.base_demand_ls):<12}"
        )

    # [RESERVOIRS]
    lines += [
        "\n[RESERVOIRS]",
        ";ID                 Head        Pattern",
    ]
    for node in network.reservoirs:
        lines.append(f" {node.id:<20}{_f(node.total_head_m):<12}")

    # [TANKS]
    lines += [
        "\n[TANKS]",
        ";ID                 Elevation   InitLevel   MinLevel    MaxLevel    Diameter    MinVol      VolCurve        Overflow",
    ]

    # [PIPES]
    lines += [
        "\n[PIPES]",
        ";ID                 Node1               Node2               Length      Diameter    Roughness   MinorLoss   Status",
    ]
    for pipe in network.pipes:
        lines.append(
            f" {pipe.id:<20}{pipe.node1:<20}{pipe.node2:<20}"
            f"{_f(pipe.comprimento_m):<12}{_f(pipe.diametro_mm):<12}"
            f"{_f(pipe.rugosidade_HW):<12}{'0':<12}Open"
        )

    # [PUMPS]
    lines += [
        "\n[PUMPS]",
        ";ID                 Node1               Node2               Parameters",
    ]

    # [VALVES]
    lines += [
        "\n[VALVES]",
        ";ID                 Node1               Node2               Diameter    Type        Setting     MinorLoss",
    ]

    # [TAGS]
    lines.append("\n[TAGS]")

    # [DEMANDS]
    lines += [
        "\n[DEMANDS]",
        ";Junction           Demand      Pattern     Category",
    ]

    # [STATUS]
    lines += [
        "\n[STATUS]",
        ";ID                 Setting",
    ]

    # [PATTERNS]
    lines += [
        "\n[PATTERNS]",
        ";ID                 Multipliers",
    ]

    # [CURVES]
    lines += [
        "\n[CURVES]",
        ";ID                 X-Value     Y-Value",
    ]

    # [CONTROLS]
    lines.append("\n[CONTROLS]")

    # [RULES]
    lines.append("\n[RULES]")

    # [ENERGY]
    lines += [
        "\n[ENERGY]",
        " Global Efficiency   75",
        " Global Price        0",
        " Demand Charge       0",
    ]

    # [EMITTERS]
    lines += [
        "\n[EMITTERS]",
        ";Junction           Coefficient",
    ]

    # [QUALITY]
    lines += [
        "\n[QUALITY]",
        ";Node               InitQual",
    ]

    # [SOURCES]
    lines += [
        "\n[SOURCES]",
        ";Node               Type        Quality     Pattern",
    ]

    # [REACTIONS]
    lines += [
        "\n[REACTIONS]",
        ";Type     Pipe/Tank",
        " Order Bulk            1",
        " Order Tank            1",
        " Order Wall            1",
        " Global Bulk           0",
        " Global Wall           0",
        " Limiting Potential    0",
        " Roughness Correlation 0",
    ]

    # [MIXING]
    lines += [
        "\n[MIXING]",
        ";Tank               Model",
    ]

    # [TIMES]
    lines += [
        "\n[TIMES]",
        " Duration            0",
        " Hydraulic Timestep  1:00",
        " Quality Timestep    0:05",
        " Pattern Timestep    1:00",
        " Pattern Start       0:00",
        " Report Timestep     1:00",
        " Report Start        0:00",
        " Statistic           None",
    ]

    # [REPORT]
    lines += [
        "\n[REPORT]",
        " Status              No",
        " Summary             No",
        " Page                0",
    ]

    # [OPTIONS]
    lines += [
        "\n[OPTIONS]",
        " Units               LPS",
        " Headloss            H-W",
        " Specific Gravity    1.0",
        " Viscosity           1.0",
        " Trials              40",
        " Accuracy            0.001",
        " CHECKFREQ           2",
        " MAXCHECK            10",
        " DAMPLIMIT           0",
        " Unbalanced          Continue 10",
        " Demand Multiplier   1.0",
        " Emitter Exponent    0.5",
        " Quality             None",
        " Diffusivity         1.0",
        " Tolerance           0.01",
    ]

    # [COORDINATES]
    lines += [
        "\n[COORDINATES]",
        ";Node               X-Coord         Y-Coord",
    ]
    for node in network.nodes:
        if node.has_coordinates():
            lines.append(
                f" {node.id:<20}{_f(node.easting, 3):<16}{_f(node.northing, 3)}"
            )

    # [VERTICES]
    lines += [
        "\n[VERTICES]",
        ";Link               X-Coord         Y-Coord",
    ]

    # [LABELS]
    lines += [
        "\n[LABELS]",
        ";X-Coord         Y-Coord          Label & Anchor Node",
    ]

    # [BACKDROP]
    lines.append("\n[BACKDROP]")

    # [END]
    lines.append("\n[END]")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera arquivo .INP do EPANET a partir do config YAML."
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Caminho para o arquivo YAML de configuração do projeto",
    )
    args = parser.parse_args()

    config  = load_config(args.config)
    network = build_network(config)

    issues = network.validate()
    if issues:
        print("\nProblemas encontrados — verifique antes de usar o INP:", file=sys.stderr)
        for issue in issues:
            print(f"  • {issue}", file=sys.stderr)

    out_path = Path.cwd() / config["output_inp"]
    write_inp(network, out_path)
    print(f"INP gerado em '{out_path}'")


if __name__ == "__main__":
    main()
