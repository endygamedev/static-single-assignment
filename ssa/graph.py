from pydot import Dot, Node, Edge, Subgraph

from .builder import NodeType, NodeData
from .statements import (
    Statement,
    IfStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
)


# Need to handle when we should mark edge as `True`
# or which edge we need to markd as `False`.
# If `IF` node already in this list, that means
# that we need the edge as `False`, because
# at the first round we mark another edge as `True`.
# `True` branch is first and `False` is the second.
IF_NODES: list[NodeData] = []


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
