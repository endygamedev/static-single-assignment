from pydot import Dot, Node, Edge, Subgraph, Cluster
from pprint import pprint
from ast import If

from .builder import NodeType, NodeData, CFGBuilder
from .statements import (
    Statement,
    IfStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
    FunctionDefStatement,
)


class GraphBuilder:
    def __init__(self, builder: CFGBuilder):
        self.statements: list[Statement] = builder.statements
        self.next_node_after_while: dict[int, int] = builder.next_node_after_while
        # self.last_if_action: dict[int, int] = builder.last_if_action

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
        self.id2node = builder.id2node

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

    def add_edge(self, previous: NodeData, current: NodeData) -> None:
        label = self.get_edge_label(previous)
        self.graph.add_edge(Edge(previous._id, current._id, label=label))

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
                            case NodeType.BREAK:
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
                label = "B"
                print(isinstance(statement.condition[1], If))
                # if (
                #     statement.is_previous_condition
                #     and self.get_edge_label(self.id2node[statement.previous].node)
                #     == "T"
                # ):
                #     label = f"T ({label})"
                # elif (
                #     statement.is_previous_condition
                #     and self.get_edge_label(self.id2node[statement.previous].node)
                #     == "F"
                # ):
                #     label = f"F ({label})"
                edge = Edge(
                    statement.source,
                    self.next_node_after_while[statement.condition[0]],
                    label=label,
                )
                self.graph.add_edge(edge)
                return
                # # graph.add_node(Node(current[0]._id, label=current[0].label, shape="box"))
                # # add_edge(graph, previous, current)

                # edge = Edge(
                #     current[0]._id - 2,
                #     self.next_node_after_while[statement.condition._id],
                # )

                # edge_list = [
                #     (edge.get_source(), edge.get_destination())
                #     for edge in self.graph.get_edge_list()
                # ]

                # print((edge.get_source(), edge.get_destination()))
                # print(edge_list)

                # if (edge.get_source(), edge.get_destination()) in edge_list:
                #     print(edge)
                # return None, self.graph
            # elif isinstance(statement, ContinueStatement):
            #     edge = Edge(
            #         self.last_if_action[statement.from_state._id],
            #         statement.condition._id,
            #         label="C",
            #     )
            #     self.graph.add_edge(edge)
            #     self.current = None
            #     self.if_nodes.append(self.last_if_action[statement.from_state._id])
            #     return
            # elif isinstance(statement, FunctionDefStatement):
            #     function_block = Cluster("cluster0", color="blue", cluster=True)
            #     function_block.add_node(
            #         Node(current[0]._id, label=current[0].label, shape="oval")
            #     )
            #     print("Cluster: " + function_block.get_name())
            #     self.graph.add_edge(
            #         Edge(
            #             previous[0]._id, current[0]._id, lhead=function_block.get_name()
            #         )
            #     )
            #     # self.graph.add_edge(Edge(previous, current))
            #     graph = self.graph
            #     self.graph = function_block
            #     body_current, _ = self.build_graph(statement.body, current)
            #     self.graph = graph
            #     graph.add_subgraph(function_block)
            #     current = body_current
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
                        if item._type is NodeType.BREAK:
                            continue
                        else:
                            self.add_edge(item, self.current[0])
