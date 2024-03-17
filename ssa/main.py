from pprint import pprint
from sys import exit
from pathlib import Path

from .builder import CFGBuilder
from .graph import GraphBuilder


def main():
    # Example of Python code
    # See `../tests/example.py` for details
    python_file = Path("./tests/test_phi_simple.py")
    python_code = python_file.read_text(encoding="utf-8")

    # Validate that syntax is correct
    try:
        compile(python_code, "", "exec")
    except SyntaxError as exc:
        print(f"Syntax Error: {exc}")
        exit(1)

    builder = CFGBuilder(python_file)
    print("STATEMENTS:")
    pprint(builder.statements)

    graph_builder = GraphBuilder(builder)
    graph = graph_builder.graph
    graph.write_png("cfg.png")  # pylint: disable=no-member
