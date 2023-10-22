from ast import (
    NodeVisitor,
    parse,
    Constant,
    Name,
    While,
    Assign,
    BinOp,
    Compare,
)
from ast import Eq, NotEq, Lt, LtE, Gt, GtE, Is, IsNot, In, NotIn
from ast import (
    Add,
    Sub,
    Mult,
    MatMult,
    Div,
    Mod,
    Pow,
    BitOr,
    BitAnd,
    BitXor,
    FloorDiv,
    LShift,
    RShift,
)
from dataclasses import dataclass

from .statements import (
    NodeData,
    NodeType,
    Statement,
    IfStatement,
    WhileStatement,
    ConditionStatement,
    BreakStatement,
    ContinueStatement,
    FunctionStatement,
    ReturnStatement,
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

OPERATORS = {
    Add: "+",
    Sub: "-",
    Mult: "*",
    MatMult: "@",
    Div: "/",
    Mod: "%",
    Pow: "**",
    LShift: "<<",
    RShift: ">>",
    BitOr: "|",
    BitXor: "^",
    BitAnd: "&",
    FloorDiv: "//",
}


@dataclass
class ForAsWhileData:
    variable: str
    step: int


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
        self.while_nodes = []
        self.node_after_while = dict()
        self.id2statement = dict()
        self.last_node_while = []
        self.id2statement[self.counter] = self.current

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
        variable = node.targets[0].id
        if isinstance(node.value, BinOp):
            # TODO: This works only for binary operations: var `op` chat
            # Example: x = x + 1
            lhs = node.value.left.id
            operator = OPERATORS[node.value.op.__class__]
            rhs = node.value.right.value
            value = f"{lhs} {operator} {rhs}"
        elif isinstance(node.value, Constant):
            value = str(node.value.n)

        label = f"{variable} = {value}"

        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.ASSIGN,
                label=label,
            )
        )
        self.statements.append(self.current)
        self.id2statement[self.counter] = self.current

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
        *,
        for_data: ForAsWhileData | None = None,
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
        statements_storage.append(condition)
        condition_id = self.counter
        self.id2statement[condition_id] = condition

        if condition_statement is WhileStatement:
            self.while_nodes.append(condition)
            self.last_node_while.append(node.body[-1])

        if for_data is not None:
            increment_assign_node = Assign(
                targets=[Name(id=for_data.variable)],
                value=BinOp(
                    left=Name(id=for_data.variable),
                    op=Add(),
                    right=Constant(value=for_data.step),
                ),
            )
            node.body.append(increment_assign_node)

        statements = self.statements
        self.statements = condition.body
        self.visit(node.body)
        self.statements = statements

        statements = self.statements
        self.statements = condition.orelse
        self.visit(node.orelse)
        self.statements = statements

        if condition_statement is WhileStatement:
            if len(self.while_nodes) >= 2 and isinstance(
                self.last_node_while[-2], While
            ):
                # If this while is inner to another while
                # and while is the last statement of outer while
                # then we need to go to outer while condition
                self.node_after_while[condition_id] = self.while_nodes[-2].node._id
            else:
                # Else we need to go to next node after while
                self.node_after_while[condition_id] = self.counter + 1
            self.last_node_while.pop()
            self.while_nodes.pop()

    def visit_If(self, node):
        self.__visit_Condition(node, self.statements, IfStatement)

    def visit_While(self, node):
        self.__visit_Condition(node, self.statements, WhileStatement)

    def visit_Break(self, node):  # pylint: disable=unused-argument
        label = "break"
        self.current = BreakStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.BREAK,
                label=label,
            ),
            while_statement=self.while_nodes[-1],
        )
        self.statements.append(self.current)
        self.id2statement[self.counter] = self.current

    def visit_Continue(self, node):  # pylint: disable=unused-argument
        label = "continue"
        self.current = ContinueStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.CONTINUE,
                label=label,
            ),
            while_statement=self.while_nodes[-1],
        )
        self.statements.append(self.current)
        self.id2statement[self.counter] = self.current

    def visit_For(self, node):
        variable = node.target.id
        match len(node.iter.args):
            case 3:  # Example: `for i in range(1, 10, 1)`
                max_value = node.iter.args[1].value
                min_value = node.iter.args[0].value
                step_value = node.iter.args[2].value
            case 2:  # Example: `for i in range(1, 10)`
                max_value = node.iter.args[1].value
                min_value = node.iter.args[0].value
                step_value = 1
            case 1:  # Example: `for i in range(10)`
                max_value = node.iter.args[0].value
                min_value = 0
                step_value = 1

        # Set basic assign case
        assign_node = Assign(targets=[Name(id=variable)], value=Constant(n=min_value))
        self.__visit_Assign(assign_node)

        # TODO: We need to interpreter FOR as WHILE
        while_node = While(
            test=Compare(
                left=Name(id=variable),
                ops=[Lt()],
                comparators=[Constant(n=max_value)],
            ),
            body=node.body,
            orelse=node.orelse,
        )
        self.counter += 1
        self.__visit_Condition(
            while_node,
            self.statements,
            WhileStatement,
            for_data=ForAsWhileData(
                variable=variable,
                step=step_value,
            ),
        )

    # This funciton need for setting all return statements
    # to the end of the function definition
    def set_end_to_return(
        self,
        statement: Statement,
        end_of_function_statement: Statement,
    ):
        if not hasattr(statement, "body"):
            if isinstance(statement, ReturnStatement):
                statement.end_of_function_statement = end_of_function_statement
        else:
            for item in statement.body:
                self.set_end_to_return(item, end_of_function_statement)

            for item in statement.orelse:
                self.set_end_to_return(item, end_of_function_statement)

    def visit_FunctionDef(self, node):
        name = node.name
        function_name = f"{name}("
        args_values = node.args.args
        args = ""
        for i, arg in enumerate(args_values):
            args += f"{arg.arg}, " if i != len(args_values) - 1 else arg.arg
        function_name += f"{args})"
        label = f"def {function_name}"

        function = FunctionStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.FUNCTION_DEF,
                label=label,
            )
        )
        self.statements.append(function)

        statements = self.statements
        self.statements = function.body
        self.visit(node.body)

        self.counter += 1
        label = f"End of {function_name}"
        function_end = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.FUNCTION_END,
                label=label,
            )
        )
        self.statements.append(function_end)
        self.current = function_end
        for statement in self.statements:
            self.set_end_to_return(statement, function_end)
        self.id2statement[self.counter] = self.current
        self.statements = statements

    def visit_Return(self, node):
        node_value = node.value
        value = ""
        if isinstance(node_value, Constant):
            value = node_value.value
        elif isinstance(node_value, Name):
            value = node_value.id

        label = f"return {value}"
        self.current = ReturnStatement(
            NodeData(
                _id=self.counter,
                _type=NodeType.RETURN,
                label=label,
            ),
        )
        self.statements.append(self.current)
        self.id2statement[self.counter] = self.current

    def visit_Call(self, node):
        label = f"{node.func.id}("
        for i, arg in enumerate(node.args):
            if isinstance(arg, Constant):
                label += f"{arg.value}, " if i != len(node.args) - 1 else f"{arg.value}"
            elif isinstance(arg, Name):
                label += f"{arg.id}, " if i != len(node.args) - 1 else arg.id
        label += ")"

        self.current = Statement(
            NodeData(
                _id=self.counter,
                _type=NodeType.CALL,
                label=label,
            ),
        )
        self.statements.append(self.current)
        self.id2statement[self.counter] = self.current

    def visit_AugAssign(self, node):
        variable = node.target.id
        assign_node = Assign(
            targets=[Name(id=variable)],
            value=BinOp(left=Name(id=variable), op=node.op, right=node.value),
        )
        self.__visit_Assign(assign_node)

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
        self.id2statement[self.counter] = self.current
