from pprint import pprint
from textwrap import dedent

from .builder import CFGBuilder
from .graph import GraphBuilder


def main():
    # Example Python code
    python_code = dedent(
        """\
        while x > 1000:
            while y > 10:
                while z > 5:
                    if y == 10:
                        break
            
        # def function(x, *, k=2):
        #     while i > 0:
        #         while j < 0:
        #             if c < 0:
        #                 y = 1
        #             elif c == 1:
        #                 continue
        #             else:
        #                 break
        #             z = 2
        #         x = 1
        #         if i == 2:
        #             break
        #     if i > 0:
        #         x = 3
        # def add(x, y):
        #     s = 1
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    graph_builder = GraphBuilder(builder)
    graph = graph_builder.graph
    graph.write_png("cfg.png")  # pylint: disable=no-member
