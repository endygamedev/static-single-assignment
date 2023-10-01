from ast import NodeVisitor, parse, Constant, Name
from ast import Gt, Eq

from .statements import (
    NodeData,
    NodeType,
    Statement,
    IfStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
    ConditionStatement,
)


COMPARATORS = {Gt: ">", Eq: "=="}


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
        self.__append_end()

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

        condition_statement = condition_statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.IF,
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

    def visit_Continue(self, node):  # pylint: disable=unused-argument
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
        raise NotImplementedError()

    def visit_Return(self, node):
        raise NotImplementedError()

    def visit_Call(self, node):
        raise NotImplementedError()

    def __append_end(self):
        self.counter += 1
        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.END,
                label="End",
            )
        )
        self.statements.append(self.current)
