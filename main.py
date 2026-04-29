"""
main.py
─────────────────────────────────────────────────────────────────────────────
Ponto de entrada único do pipeline corsan-to-epanet.

Executa as duas fases em sequência:
  1. reader     — lê CSV + XLSX e monta o objeto Network
  2. inp_writer — gera o arquivo .INP do EPANET

Uso:
    python main.py config/gravatai_p96.yaml
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.inp_writer import write_inp
from src.reader import _prompt_missing_coordinates, build_network, load_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pipeline completo: CSV + XLSX CORSAN → JSON → INP EPANET."
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Caminho para o arquivo YAML de configuração do projeto",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # 1. Leitura e montagem da rede
    print(f"Lendo dados do projeto '{config.get('projeto_nome', '')}'...")
    network = build_network(config)

    csv_path = Path.cwd() / config["csv_path"]
    _prompt_missing_coordinates(network, csv_path)

    # 2. Validação
    issues = network.validate()
    if issues:
        print("\nProblemas encontrados:", file=sys.stderr)
        for issue in issues:
            print(f"  • {issue}", file=sys.stderr)

    print(network.summary())

    # 3. Exportar JSON
    output_json = config.get("output_json")
    if output_json:
        out_json = Path.cwd() / output_json
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(network.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\nJSON salvo em '{out_json}'")

    # 4. Gerar INP
    output_inp = config.get("output_inp")
    if output_inp:
        out_inp = Path.cwd() / output_inp
        write_inp(network, out_inp)
        print(f"INP  salvo em '{out_inp}'")
    else:
        print("AVISO: 'output_inp' não definido no config — INP não gerado.", file=sys.stderr)


if __name__ == "__main__":
    main()
