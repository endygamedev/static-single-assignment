from pydot import Dot, Node, Edge, Subgraph, Cluster

from .builder import NodeType, NodeData, CFGBuilder
from .statements import (
    Statement,
    IfStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
    FunctionStatement,
)


class GraphBuilder:
    def __init__(self, builder: CFGBuilder):
        self.statements: list[Statement] = builder.statements

        self.graph: Dot = Dot(graph_type="digraph", compound="true")
        self.current = None
        self.previous = None

        # Need to handle when we should mark edge as `True`
        # or which edge we need to mark it as `False`.
        # If `IF` node already in this list, that means
        # that we need the edge as `False`, because
        # at the first round we mark another edge as `True`.
        # `True` branch is first and `False` is the second.
        self.if_nodes: list[NodeData] = []
        self.id2statement = builder.id2statement
        self.node_after_while = builder.node_after_while

        # This thing need for function definition block
        self.current_function_cluster = None

        # Build graph
        self.build()

    @staticmethod
    def get_color(node_type: NodeType) -> str:
        match node_type:
            case NodeType.START:
                return "green"
            case NodeType.END:
                return "red"
            case _:
                return "white"

    @staticmethod
    def get_shape(node_type: NodeType) -> str:
        match node_type:
            case NodeType.START | NodeType.END:
                return "oval"
            case _:
                return "box"

    def get_edge_label(self, previous: NodeData) -> str:
        match previous._type:
            case NodeType.IF if previous in self.if_nodes:
                return "F"
            case NodeType.IF:
                self.if_nodes.append(previous)
                return "T"
            case _:
                return ""

    def add_edge(
        self,
        previous: NodeData,
        current: NodeData,
        *,
        is_break=False,
        is_continue=False,
        ltail="",
        lhead="",
    ) -> None:
        # "is_break" and "is_continue"
        # cannot be assigned "True" both
        assert not is_break or not is_continue

        label = self.get_edge_label(previous)

        # Label for "break" branch
        if is_break and label != "":
            label = f"{label} (B)"
        elif is_break:
            label = "B"

        # Label for "continue" branch
        if is_continue and label != "":
            label = f"{label} (C)"
        elif is_continue:
            label = "C"

        self.graph.add_edge(
            Edge(previous._id, current._id, label=label, ltail=ltail, lhead=lhead)
        )

    def build(self):
        for statement in self.statements:
            self.previous, self.current = self.current, [statement.node]
            if isinstance(statement, WhileStatement):
                self.graph.add_node(
                    Node(
                        self.current[0]._id,
                        label=self.current[0].label,
                        shape="diamond",
                    )
                )

                if self.previous is not None:
                    for item in self.previous:
                        self.add_edge(item, self.current[0])

                current = self.current
                statements, self.statements = self.statements, statement.body
                self.build()
                self.current, body_current = current, self.current
                self.statements = statements

                if body_current is not None:
                    for item in body_current:
                        match item._type:
                            case NodeType.BREAK | NodeType.CONTINUE:
                                current.append(item)
                            case _:
                                self.add_edge(item, current[0])
            elif isinstance(statement, IfStatement):
                self.graph.add_node(
                    Node(
                        self.current[0]._id,
                        label=self.current[0].label,
                        shape="diamond",
                    )
                )

                if self.previous is not None:
                    for item in self.previous:
                        self.add_edge(item, self.current[0])

                current = self.current
                statements, self.statements = self.statements, statement.body
                self.build()
                self.current, body_current = current, self.current
                self.statements = statements

                current = self.current
                statements, self.statements = self.statements, statement.orelse
                self.build()
                self.current, orelse_current = current, self.current
                self.statements = statements

                if body_current is None:
                    self.current = orelse_current
                elif orelse_current is None:
                    self.current = body_current
                else:
                    self.current = body_current + orelse_current
            elif isinstance(statement, BreakStatement):
                while_statement = statement.while_statement.node._id
                for item in self.previous:
                    self.add_edge(
                        item,
                        self.id2statement[self.node_after_while[while_statement]].node,
                        is_break=True,
                    )
                return
            elif isinstance(statement, ContinueStatement):
                for item in self.previous:
                    self.add_edge(
                        item,
                        statement.while_statement.node,
                        is_continue=True,
                    )
                return
            elif isinstance(statement, FunctionStatement):
                self.current_function_cluster = None
                function_cluster = Cluster(self.current[0].label)

                function_node = Node(
                    self.current[0]._id,
                    label=self.current[0].label,
                    shape="egg",
                )
                self.graph.add_node(function_node)

                for item in self.previous:
                    self.add_edge(
                        item,
                        self.current[0],
                        ltail=function_cluster.get_name(),
                        lhead=function_cluster.get_name(),
                    )

                # Pre
                current = self.current
                statements, self.statements = self.statements, statement.body
                graph, self.graph = self.graph, function_cluster

                # Build body
                self.build()

                # Post
                self.current, body_current = current, self.current
                self.statements = statements
                self.graph = graph
                self.graph.add_subgraph(function_cluster)
                self.current = [statement.last_function_node.node]
                self.current_function_cluster = function_cluster
            elif isinstance(statement, Statement):
                color = self.get_color(self.current[0]._type)
                shape = self.get_shape(self.current[0]._type)
                node = Node(
                    self.current[0]._id,
                    label=self.current[0].label,
                    shape=shape,
                    style="filled",
                    fillcolor=color,
                )

                match self.current[0]._type:
                    case NodeType.END:
                        subgraph = Subgraph(rank="sink")
                        subgraph.add_node(node)
                        self.graph.add_subgraph(subgraph)
                    case _:
                        self.graph.add_node(node)

                if self.previous is not None:
                    for item in self.previous:
                        match item._type:
                            case NodeType.BREAK | NodeType.CONTINUE:
                                continue
                            case _:
                                if self.current_function_cluster is not None:
                                    # This case needs when we have last
                                    # function definition block
                                    self.add_edge(
                                        item,
                                        self.current[0],
                                        ltail=self.current_function_cluster.get_name(),
                                    )
                                else:
                                    self.add_edge(item, self.current[0])
