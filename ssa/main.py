from pprint import pprint
from textwrap import dedent

from .builder import CFGBuilder
from .graph import GraphBuilder


def main():
    # Example Python code
    python_code = dedent(
        """\
        if x > 10:
            y = 20

        def function(x, y, z):
            x = 100
            for i in range(10):
                continue
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    graph_builder = GraphBuilder(builder)
    graph = graph_builder.graph
    graph.write_png("cfg.png")  # pylint: disable=no-member
