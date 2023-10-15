from ast import NodeVisitor, parse, Constant, Name, While
from ast import Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn

from .statements import (
    NodeData,
    NodeType,
    Statement,
    IfStatement,
    WhileStatement,
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
        for i, arg in enumerate(args):
            label += f"{arg}, " if i < len(args) - 1 else arg
        label += ")"

        function_statement = FunctionDefStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.FUNCTION_DEF,
                label=label,
            ),
            function_id=self.function_counter,
        )
        self.statements.append(function_statement)
        self.function_counter += 1

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
        self.id2node[self.counter] = condition

        if condition_statement is WhileStatement:
            self.break_targets.append((self.counter, node.body[-1]))

        statements_storage.append(condition)

        statements = self.statements
        self.statements = condition.body
        self.visit(node.body)
        self.statements = statements

        statements = self.statements
        self.statements = condition.orelse
        if condition_statement is IfStatement:
            if len(node.orelse) == 1:
                node.orelse[0].condition_statement = condition.node._id
        self.visit(node.orelse)
        self.statements = statements

        if condition_statement is WhileStatement:
            if len(self.break_targets) > 1 and (
                isinstance(self.break_targets[-2][1], While)
            ):
                _target = self.break_targets[-2][0]
            else:
                item = condition.body[-1]
                _target = item.node._id + 1
                while isinstance(item, IfStatement):
                    item = item.body[-1]
                    _target = item.node._id + 1
            print(_target)
            self.next_node_after_while[self.break_targets[-1][0]] = _target
            self.break_targets.pop()

    def visit_If(self, node):
        self.__visit_Condition(node, self.statements, IfStatement)

    def visit_While(self, node):
        self.__visit_Condition(node, self.statements, WhileStatement)

    def visit_Break(self, node):  # pylint: disable=unused-argument
        if not hasattr(node, "condition_statement"):
            source = self.counter - 1
        else:
            source = node.condition_statement
        self.current = BreakStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.BREAK,
                label="break",
            ),
            condition=self.break_targets[-1],
            source=source,
        )
        self.statements.append(self.current)

    def visit_Continue(self, node):  # pylint: disable=unused-argument
        pass
        # self.current = ContinueStatement(
        #     NodeData(
        #         _id=self.counter,
        #         _type=NodeType.CONTINUE,
        #         label="continue",
        #     ),
        #     from_state=self.continue_targets[-1].node,
        #     condition=self.break_targets[-1].node,
        # )
        # self.statements.append(self.current)

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
