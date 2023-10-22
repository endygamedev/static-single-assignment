from pprint import pprint
from textwrap import dedent
from sys import exit

from .builder import CFGBuilder
from .graph import GraphBuilder


def main():
    # Example Python code
    python_code = dedent(
        """\
        return 4
        """
    )

    try:
        compile(python_code, "", "exec")
    except SyntaxError as exc:
        print(f"Syntax Error: {exc}")
        exit(1)

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    graph_builder = GraphBuilder(builder)
    graph = graph_builder.graph
    graph.write_png("cfg.png")  # pylint: disable=no-member
