from ast import NodeVisitor, parse, Constant, Name
from ast import Gt, Eq
from enum import Enum, auto
from dataclasses import dataclass, field
from pprint import pprint
from textwrap import dedent
from typing import TypeVar

from pydot import Dot, Node, Edge, Subgraph


COMPARATORS = {Gt: ">", Eq: "=="}


# Need to handle when we should mark edge as `True`
# or which edge we need to markd as `False`.
# If `IF` node already in this list, that means
# that we need the edge as `False`, because
# at the first round we mark another edge as `True`.
# `True` branch is first and `False` is the second.
IF_NODES = []


class NodeType(Enum):
    NULL = auto()
    START = auto()
    ASSIGN = auto()
    IF = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()
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
    body: list[Statement] = field(default_factory=list)
    orelse: list[Statement] = field(default_factory=list)


class WhileStatement(IfStatement):
    pass


class BreakStatement(Statement):
    pass


class ContinueStatement(Statement):
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
        self.statements.append(self.current)

    def visit_Assign(self, node):
        if isinstance(node, list):
            for item in node:
                self.__visit_Assign(item)
        else:
            self.__visit_Assign(node)

    def __visit_Condition(
        self,
        node,
        statements_storage,
        condition_statement: ConditionStatement,
    ):
        lhs = node.test.left.id
        comparator = COMPARATORS[node.test.ops[0].__class__]
        rhs = ""
        if isinstance(node.test.comparators[0], Constant):
            rhs = node.test.comparators[0].value
        elif isinstance(node.test.comparators[0], Name):
            rhs = node.test.comparators[0].id
        label = f"{lhs} {comparator} {rhs}"

        condition_statement_type = (
            NodeType.WHILE if condition_statement is WhileStatement else NodeType.IF
        )

        condition_statement = condition_statement(
            NodeData(
                _id=self.counter,
                _type=condition_statement_type,
                label=label,
            )
        )

        statements_storage.append(condition_statement)

        statements = self.statements
        self.statements = condition_statement.body
        self.visit(node.body)
        self.statements = statements

        statements = self.statements
        self.statements = condition_statement.orelse
        self.visit(node.orelse)
        self.statements = statements

    def visit_If(self, node):
        self.__visit_Condition(node, self.statements, IfStatement)

    def visit_While(self, node):
        self.__visit_Condition(node, self.statements, WhileStatement)

    def visit_Break(self, node):  # pylint: disable=unused-argument
        self.current = BreakStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.BREAK,
                label="break",
            )
        )
        self.statements.append(self.current)

    def visit_Continue(self, node):
        self.current = ContinueStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.CONTINUE,
                label="continue",
            )
        )
        self.statements.append(self.current)

    def visit_For(self, node):
        print(node._fields)
        print(node.target.id)  # `i`
        print(node.body)  # <cycle body>
        print(node.iter.func.id)  # `range`
        print(node.iter.args[0].value)  # <min value in range>
        print(node.iter.args[1].value)  # <max value in range>

        # TODO: Implement `for`-handling
        raise NotImplementedError()

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


def get_edge_label(previous: NodeData) -> str:
    if previous._type is NodeType.IF and previous in IF_NODES:
        return "F"
    elif previous._type is NodeType.IF:
        IF_NODES.append(previous)
        return "T"
    else:
        return ""


def add_edge(graph: Dot, previous: list[Node], current: list[Node]) -> None:
    if previous is not None:
        for item in previous:
            label = get_edge_label(item)
            graph.add_edge(Edge(item._id, current[0]._id, label=label))


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
            for item in body_current:
                match item._type:
                    case NodeType.BREAK:
                        current.append(item)
                    case _:
                        add_edge(graph, [item], current)
        elif isinstance(statement, IfStatement):
            graph.add_node(
                Node(current[0]._id, label=current[0].label, shape="diamond")
            )
            add_edge(graph, previous, current)
            body_current, _ = build_graph(statement.body, graph, current)
            orelse_current, _ = build_graph(statement.orelse, graph, current)
            current = body_current + orelse_current
        elif isinstance(statement, BreakStatement) or isinstance(
            statement, ContinueStatement
        ):
            graph.add_node(Node(current[0]._id, label=current[0].label, shape="box"))
            add_edge(graph, previous, current)
            return current, graph
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
        while i > 0:
            if c == 0:
                x = 1
                x = 2
            else:
                continue
            x = 1
        """
    )

    builder = CFGBuilder(python_code)
    pprint(builder.statements)

    _, graph = build_graph(builder.statements)
    graph.write_png("cfg.png")
