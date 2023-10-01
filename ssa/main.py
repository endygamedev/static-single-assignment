from pprint import pprint
from textwrap import dedent

from .builder import CFGBuilder
from .graph import build_graph


def main():
    # Example Python code
    python_code = dedent(
        """\
        while i > 0:
            if c == 0:
                x = 1
                x = 2
            elif c == 1:
                continue
            else:
                break
            x = 1
        if i > 0:
            x = 3
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    _, graph = build_graph(builder.statements)
    graph.write_png("cfg.png")
