from ast import NodeVisitor, parse, Constant, Name
from ast import Gt, Eq
from enum import Enum, auto
from dataclasses import dataclass
from pprint import pprint
from textwrap import dedent
from typing import TypeVar

from pydot import Dot, Node, Edge, Subgraph


COMPARATORS = {Gt: ">", Eq: "=="}


class NodeType(Enum):
    NULL = auto()
    START = auto()
    ASSIGN = auto()
    IF = auto()
    END = auto()


@dataclass
class NodeData:
    _id: int
    _type: NodeType
    label: str


@dataclass
class Statement:
    node: NodeData


@dataclass
class IfStatement(Statement):
    body: list[Statement] | None = None
    orelse: list[Statement] | None = None


class WhileStatement(IfStatement):
    pass


ConditionStatement = TypeVar("ConditionStatement", IfStatement, WhileStatement)


class CFGBuilder(NodeVisitor):
    def __init__(self, input_code: str) -> None:
        # Build AST
        tree = parse(input_code)

        # Initialize attributes
        self.counter = 0
        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.START,
                label="Start",
            )
        )
        self.statements = [self.current]
        self.inner_if = False
        self.inner_if_statements = []

        # Run visit process
        self.visit(tree)
        self.append_end()

    def __visit(self, node):
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        self.counter += 1
        return visitor(node)

    def visit(self, node):
        if isinstance(node, list):
            for item in node:
                self.__visit(item)
        else:
            self.__visit(node)

    def __visit_Assign(self, node):
        label = f"{node.targets[0].id} = {node.value.n}"
        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.ASSIGN,
                label=label,
            )
        )
        if not self.inner_if:
            self.statements.append(self.current)
        else:
            self.inner_if_statements.append(self.current)

    def visit_Assign(self, node):
        if isinstance(node, list):
            for item in node:
                self.__visit_Assign(item)
        else:
            self.__visit_Assign(node)

    def __visit_If(
        self,
        node,
        statements_storage,
        condition_statement: ConditionStatement = IfStatement,
    ):
        self.inner_if = True

        lhs = node.test.left.id
        comparator = COMPARATORS[node.test.ops[0].__class__]

        rhs = ""
        if isinstance(node.test.comparators[0], Constant):
            rhs = node.test.comparators[0].value
        elif isinstance(node.test.comparators[0], Name):
            rhs = node.test.comparators[0].id
        label = f"{lhs} {comparator} {rhs}"

        if_statement = condition_statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.IF,
                label=label,
            )
        )

        statements_storage.append(if_statement)

        if_statement.body = []
        self.inner_if_statements = if_statement.body
        self.visit(node.body)

        if_statement.orelse = []
        self.inner_if_statements = if_statement.orelse
        self.visit(node.orelse)

        self.inner_if = False

    def visit_If(self, node):
        if self.inner_if:
            self.__visit_If(node, self.inner_if_statements)
        else:
            self.__visit_If(node, self.statements)

    def visit_While(self, node):
        if self.inner_if:
            self.__visit_If(node, self.inner_if_statements, WhileStatement)
        else:
            self.__visit_If(node, self.statements, WhileStatement)

    def append_end(self):
        self.counter += 1
        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.END,
                label="End",
            )
        )
        self.statements.append(self.current)


def get_color(node_type: NodeType) -> str:
    match node_type:
        case NodeType.START:
            return "green"
        case NodeType.END:
            return "red"
        case _:
            return "white"


def get_shape(node_type: NodeType) -> str:
    return "oval" if node_type is NodeType.START or node_type is NodeType.END else "box"


def add_edge(graph: Dot, previous: list[Node], current: list[Node]) -> None:
    if previous is not None:
        for item in previous:
            graph.add_edge(Edge(item._id, current[0]._id))


def build_graph(
    statements: list[Statement],
    graph: Dot = Dot(graph_type="digraph"),
    current: list[Node] = None,
):
    for statement in statements:
        previous, current = current, [statement.node]
        if isinstance(statement, WhileStatement):
            graph.add_node(
                Node(current[0]._id, label=current[0].label, shape="diamond")
            )
            add_edge(graph, previous, current)
            body_current, _ = build_graph(statement.body, graph, current)
            add_edge(graph, body_current, current)
        elif isinstance(statement, IfStatement):
            graph.add_node(
                Node(current[0]._id, label=current[0].label, shape="diamond")
            )
            add_edge(graph, previous, current)
            body_current, _ = build_graph(statement.body, graph, current)
            orelse_current, _ = build_graph(statement.orelse, graph, current)
            current = body_current + orelse_current
        elif isinstance(statement, Statement):
            color = get_color(current[0]._type)
            shape = get_shape(current[0]._type)
            node = Node(
                current[0]._id,
                label=current[0].label,
                shape=shape,
                style="filled",
                fillcolor=color,
            )
            if current[0]._type is NodeType.END:
                subgraph = Subgraph(rank="sink")
                subgraph.add_node(node)
                graph.add_subgraph(subgraph)
            else:
                graph.add_node(node)
            add_edge(graph, previous, current)
    return current, graph


def main():
    # Example Python code
    python_code = dedent(
        """\
    x = 1

    while z > 2:
        if x > 2:
            y = 2
            c = 1
        elif x == 2:
            y = 3
            c = 2
        else:
            y = 4
    
    z = 6
    """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    _, graph = build_graph(builder.statements)
    graph.write_png("cfg.png")
