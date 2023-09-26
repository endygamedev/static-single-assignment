from ast import NodeVisitor, Gt, parse
from enum import Enum, auto
from dataclasses import dataclass

from pydot import Dot, Edge, Node


symbol = {Gt: ">"}


class NodeType(Enum):
    NULL = auto()
    ASSIGN = auto()
    IF = auto()


@dataclass(unsafe_hash=True)
class NodeData:
    name: str
    _type: NodeType

class CFGBuilder(NodeVisitor):
    def __init__(self):
        self.graph = Dot(graph_type='digraph')
        self.previous_node = None
        self.current_node = None
            
    def __visit(self, node):
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def visit(self, node):
        if isinstance(node, list):
            for item in node:
                self.__visit(item)
        else:
            self.__visit(node)

    def __visit_Assign(self, node):
        if self.current_node is not None:
            if self.current_node._type == NodeType.ASSIGN:
                self.previous_node = self.current_node
                self.current_node = NodeData(f"{self.previous_node.name}\n{node.targets[0].id} = {node.value.n}", NodeType.ASSIGN)
            elif self.current_node._type == NodeType.IF:
                self.previous_node = self.current_node
                self.current_node = NodeData(f"{node.targets[0].id} = {node.value.n}", NodeType.ASSIGN)
            else:
                self.previous_node = self.current_node
                self.current_node = NodeData(f"{node.targets[0].id} = {node.value.n}", NodeType.ASSIGN)
                self.graph.add_edge(Edge(self.previous_node.name, self.current_node.name))
        else:
            self.current_node = NodeData(f"{node.targets[0].id} = {node.value.n}", NodeType.ASSIGN)

    def visit_Assign(self, node):
        if isinstance(node, list):
            for item in node:
                self.__visit_Assign(item)
        else:
            self.__visit_Assign(node)

    def visit_If(self, node):
        lhs = node.test.left.id
        ops = symbol[node.test.ops[0].__class__]
        rhs = node.test.comparators[0].id
        if self.current_node is not None:
            self.current_node, self.previous_node = NodeData(f"{lhs} {ops} {rhs}", NodeType.IF), self.current_node
            self.graph.add_edge(Edge(self.previous_node.name, self.current_node.name))
        else:
            self.current_node = NodeData(f"{lhs} {ops} {rhs}", NodeType.IF)
        condition_node = self.current_node
        
        self.visit(node.body)
        body_node = self.current_node
        self.graph.add_edge(Edge(condition_node.name, body_node.name, label="True"))

        self.current_node = condition_node 

        self.visit(node.orelse)
        orelse_node = self.current_node
        
        self.current_node = NodeData("out", NodeType.NULL)
        self.graph.add_edge(Edge(body_node.name, self.current_node.name))
        
        if node.orelse[0].__class__.__name__ != "If":
            self.graph.add_edge(Edge(condition_node.name, orelse_node.name, label="False"))
            self.graph.add_edge(Edge(orelse_node.name, self.current_node.name))


def generate_cfg_from_python_code(input_code):
    tree = parse(input_code)
    builder = CFGBuilder()
    builder.visit(tree)
    return builder

# Example Python code
python_code = """
x = 1
y = 2

if x > y:
    x = 3
    c = 2
    z = 3
elif x > c:
    z = 2
    k = 2
else:
    y = 3
    z = 2
c = 3
"""

def main():
    builder = generate_cfg_from_python_code(python_code)
    graph = builder.graph
    graph.write_png("cfg.png")

