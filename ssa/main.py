from pprint import pprint
from textwrap import dedent

from .builder import CFGBuilder
from .graph import build_graph


def main():
    # Example Python code
    python_code = dedent(
        """\
        while i > 0:
            while j < 0:
                if c < 0:
                    y = 1
                elif c == 1:
                    continue
                else:
                    break
                z = 2
            x = 1
            continue
        if i > 0:
            x = 3
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    _, graph = build_graph(builder.statements)
    graph.write_png("cfg.png")
