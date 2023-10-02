from ast import NodeVisitor, parse, Constant, Name
from ast import Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn

from .statements import (
    NodeData,
    NodeType,
    Statement,
    IfStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
    ConditionStatement,
    FunctionDefStatement,
)


COMPARATORS = {
    Eq: "==",
    NotEq: "!=",
    Lt: "<",
    LtE: "<=",
    Gt: ">",
    GtE: ">=",
    Is: "is",
    IsNot: "is not",
    In: "in",
    NotIn: "not in",
}

WHILE_NEXT_NODE = {}


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
        self.break_targets = []

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

    def visit_FunctionDef(self, node):
        function = node.name
        args = [arg.arg for arg in (node.args.args + node.args.kwonlyargs)]

        label = f"{function}("
        for arg in args:
            label += f"{arg}, "
        label += ")"

        function_statement = FunctionDefStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.FUNCTION_DEF,
                label=label,
            )
        )
        self.statements.append(function_statement)

        statements = self.statements
        for item in node.body:
            self.statements = function_statement.body
            self.visit(item)
        self.statements = statements

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

        condition = condition_statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.IF,
                label=label,
            )
        )

        if condition_statement is WhileStatement:
            self.break_targets.append(condition)

        statements_storage.append(condition)

        statements = self.statements
        self.statements = condition.body
        self.visit(node.body)
        self.statements = statements

        statements = self.statements
        self.statements = condition.orelse
        self.visit(node.orelse)
        self.statements = statements

        if condition_statement is WhileStatement:
            WHILE_NEXT_NODE[self.break_targets[-1].node._id] = self.counter + 1
            self.break_targets.pop()

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
            ),
            condition=self.break_targets[-1].node,
        )
        self.statements.append(self.current)

    def visit_Continue(self, node):  # pylint: disable=unused-argument
        self.current = ContinueStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.CONTINUE,
                label="continue",
            ),
            condition=self.break_targets[-1].node,
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
