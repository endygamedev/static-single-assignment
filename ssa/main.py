from pprint import pprint
from textwrap import dedent

from .builder import CFGBuilder
from .graph import GraphBuilder


def main():
    # Example Python code
    python_code = dedent(
        """\
        while x > 1000:
            u = 2000
            while x > 2000:
                if x > 10:
                    y = 20
                    z = 10
                elif x > 10:
                    break
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    graph_builder = GraphBuilder(builder)
    graph = graph_builder.graph
    graph.write_png("cfg.png")  # pylint: disable=no-member
