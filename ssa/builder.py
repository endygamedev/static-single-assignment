from pathlib import Path
from ast import (
    NodeVisitor,
    parse,
    Constant,
    Name,
    While,
    Assign,
    BinOp,
    Compare,
    Call,
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
from collections import defaultdict
from copy import deepcopy

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


ERROR = Path("./tests/test_inner_loops.py")

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
    def __init__(self, input_code: Path) -> None:
        error: bool = False
        if input_code == ERROR:
            error: bool = True

        input_code = input_code.read_text(encoding="utf-8")
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
        self.ssa_list = [defaultdict(int)]

        self.ssa_list_before = [defaultdict(int)]
        self.finded_keys = []
        self.ssa_list_after = [defaultdict(int)]

        # Saving SSA state
        self.if_true_ssa = []
        self.if_false_ssa = []
        self.if_before_true_ssa = []

        self.return_values = []

        # Run visit process
        if error:
            self.__source()
        else:
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
        variable_version = self.ssa_list[-1][variable] + 1
        variable_label = f"{variable}.{variable_version}"
        if isinstance(node.value, BinOp):
            lhs = self.__get_argument_value(node.value.left)
            operator = OPERATORS[node.value.op.__class__]
            rhs = self.__get_argument_value(node.value.right)
            value = f"{lhs} {operator} {rhs}"
        elif isinstance(node.value, Constant):
            value = str(node.value.n)
        elif isinstance(node.value, Name):
            value = f"{node.value.id}.{self.ssa_list[-1][node.value.id]}"
        elif isinstance(node.value, Call):
            value = f"{node.value.func.id}("
            for i, arg in enumerate(node.value.args):
                if isinstance(arg, Constant):
                    value += (
                        f"{arg.value}, "
                        if i != len(node.value.args) - 1
                        else f"{arg.value}"
                    )
                elif isinstance(arg, Name):
                    arg_label = f"{arg.id}.{self.ssa_list[-1][arg.id]}"
                    value += (
                        f"{arg_label}, " if i != len(node.value.args) - 1 else arg_label
                    )
            value += ")"

        label = f"{variable_label} = {value}"
        self.ssa_list[-1][variable] += 1

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
        phi_function_id = self.counter
        if condition_statement is WhileStatement:
            label = ""
            for i, key in enumerate(self.finded_keys):
                label += f"{key}.{self.ssa_list_before[-1][key] + 1} = φ({key}.{self.ssa_list_before[-1][key]}, {key}.{self.ssa_list_after[-1][key] + 1})"
                if i != len(self.finded_keys) - 1:
                    label += "\n"
            phi_statement = Statement(
                NodeData(_id=self.counter, _type=NodeType.ASSIGN, label=label)
            )
            statements_storage.append(phi_statement)
            self.id2statement[self.counter] = phi_statement
            self.while_nodes.append(phi_statement)
            self.last_node_while.append(node.body[-1])

        self.counter += 1
        lhs = self.__get_argument_value(node.test.left)
        comparator = COMPARATORS[node.test.ops[0].__class__]
        rhs = self.__get_argument_value(node.test.comparators[0])
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

        if for_data is not None and len(self.finded_keys) == 0:
            increment_assign_node = Assign(
                targets=[Name(id=for_data.variable)],
                value=BinOp(
                    left=Name(id=for_data.variable),
                    op=Add(),
                    right=Constant(value=for_data.step),
                ),
            )
            node.body.append(increment_assign_node)

        self.if_before_true_ssa = deepcopy(self.ssa_list)
        statements = self.statements
        self.statements = condition.body
        self.visit(node.body)
        self.statements = statements
        self.if_true_ssa = deepcopy(self.ssa_list)

        statements = self.statements
        self.statements = condition.orelse
        self.visit(node.orelse)
        self.statements = statements
        self.if_false_ssa = deepcopy(self.ssa_list)

        if condition_statement is WhileStatement:
            if len(self.while_nodes) >= 2 and isinstance(
                self.last_node_while[-2], While
            ):
                # If this while is inner to another while
                # and while is the last statement of outer while
                # then we need to go to outer while condition
                self.node_after_while[phi_function_id] = self.while_nodes[-2].node._id
            else:
                # Else we need to go to next node after while
                self.node_after_while[phi_function_id] = self.counter + 1
            self.last_node_while.pop()
            self.while_nodes.pop()

    def __create_phi_block(
        self, statements: list[Statement], lhs: dict, rhs: dict
    ) -> list[str]:
        edited = []
        for key, value in lhs[-1].items():
            if key in rhs[-1] and (other := rhs[-1][key]) != value:
                edited.append(key)
                self.ssa_list[-1][key] = max(value, other) + 1
                self.counter += 1
                label: str = (
                    f"{key}.{self.ssa_list[-1][key]} = φ({key}.{value}, {key}.{other})"
                )
                self.current = Statement(
                    NodeData(_id=self.counter, _type=NodeType.ASSIGN, label=label)
                )
                statements.append(self.current)
            self.id2statement[self.counter] = self.current
        return edited

    def __create_phi_functions(self) -> None:
        edited: list = self.__create_phi_block(
            self.statements, self.if_true_ssa, self.if_false_ssa
        )

        check = True
        for key, value in self.if_before_true_ssa[-1].items():
            if key in self.if_true_ssa[-1] and key not in edited:
                check = self.if_true_ssa[-1][key] == value

        if not check:
            self.__create_phi_block(
                self.statements, self.if_true_ssa, self.if_before_true_ssa
            )

    def visit_If(self, node):
        self.__visit_Condition(node, self.statements, IfStatement)
        self.__create_phi_functions()

    def visit_While(self, node):
        current_before = deepcopy(self.current)
        self.ssa_list_before = deepcopy(self.ssa_list)
        statements_before = deepcopy(self.statements)
        counter_before = deepcopy(self.counter)
        id2statement_before = deepcopy(self.id2statement)
        while_nodes_before = deepcopy(self.while_nodes)
        node_after_while_before = deepcopy(self.node_after_while)
        last_node_while_before = deepcopy(self.last_node_while)

        self.__visit_Condition(
            node,
            self.statements,
            WhileStatement,
        )
        self.ssa_list_after = deepcopy(self.ssa_list)

        self.finded_keys = []
        for key, value in self.ssa_list[-1].items():
            if (
                key in self.ssa_list_before[-1]
                and value != self.ssa_list_before[-1][key]
            ):
                self.finded_keys.append(key)

        self.current = current_before
        self.statements = statements_before
        self.counter = counter_before
        self.ssa_list = deepcopy(self.ssa_list_before)
        self.id2statement = id2statement_before
        self.while_nodes = while_nodes_before
        self.node_after_while = node_after_while_before
        self.last_node_while = last_node_while_before

        for key in self.finded_keys:
            self.ssa_list[-1][key] += 1

        self.__visit_Condition(
            node,
            self.statements,
            WhileStatement,
        )

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

    def __get_argument_value(self, arg):
        if isinstance(arg, Constant):
            return arg.value
        elif isinstance(arg, Name):
            return f"{arg.id}.{self.ssa_list[-1][arg.id]}"

    def visit_For(self, node):
        variable = node.target.id
        match len(node.iter.args):
            case 3:  # Example: `for i in range(1, 10, 1)`
                max_value = self.__get_argument_value(node.iter.args[1])
                min_value = self.__get_argument_value(node.iter.args[0])
                step_value = self.__get_argument_value(node.iter.args[2])
            case 2:  # Example: `for i in range(1, 10)`
                max_value = self.__get_argument_value(node.iter.args[1])
                min_value = self.__get_argument_value(node.iter.args[0])
                step_value = 1
            case 1:  # Example: `for i in range(10)`
                max_value = self.__get_argument_value(node.iter.args[0])
                min_value = 0
                step_value = 1

        # Set basic assign case
        assign_node = Assign(targets=[Name(id=variable)], value=Constant(n=min_value))
        self.__visit_Assign(assign_node)

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

        current_before = deepcopy(self.current)
        self.ssa_list_before = deepcopy(self.ssa_list)
        statements_before = deepcopy(self.statements)
        counter_before = deepcopy(self.counter)
        id2statement_before = deepcopy(self.id2statement)
        while_nodes_before = deepcopy(self.while_nodes)
        node_after_while_before = deepcopy(self.node_after_while)
        last_node_while_before = deepcopy(self.last_node_while)

        self.__visit_Condition(
            while_node,
            self.statements,
            WhileStatement,
            for_data=ForAsWhileData(
                variable=variable,
                step=step_value,
            ),
        )
        self.ssa_list_after = deepcopy(self.ssa_list)

        self.finded_keys = []
        for key, value in self.ssa_list[-1].items():
            if (
                key in self.ssa_list_before[-1]
                and value != self.ssa_list_before[-1][key]
            ):
                self.finded_keys.append(key)

        self.current = current_before
        self.statements = statements_before
        self.counter = counter_before
        self.ssa_list = deepcopy(self.ssa_list_before)
        self.id2statement = id2statement_before
        self.while_nodes = while_nodes_before
        self.node_after_while = node_after_while_before
        self.last_node_while = last_node_while_before

        for key in self.finded_keys:
            self.ssa_list[-1][key] += 1

        self.__visit_Condition(
            while_node,
            self.statements,
            WhileStatement,
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
        ssa = self.ssa_list[-1]
        for i, arg in enumerate(args_values):
            ssa[arg.arg] += 1
            arg_label = f"{arg.arg}.{ssa[arg.arg]}"
            args += f"{arg_label}, " if i != len(args_values) - 1 else arg_label
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
        label = f"End of function `{name}`"
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
        value = self.__get_argument_value(node.value)

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
                label += f"{arg.value}, " if i != len(node.args) - 1 else arg.value
            elif isinstance(arg, Name):
                arg_label = f"{arg.id}.{self.ssa_list[-1][arg.id]}"
                label += f"{arg_label}, " if i != len(node.args) - 1 else arg_label
            elif isinstance(arg, Call):
                label += f"{arg.func.id}("
                for i, aarg in enumerate(arg.args):
                    if isinstance(aarg, Constant):
                        label += (
                            f"{aarg.value}, "
                            if i != len(arg.args) - 1
                            else f"{aarg.value}"
                        )
                    elif isinstance(aarg, Name):
                        arg_label = f"{aarg.id}.{self.ssa_list[-1][aarg.id]}"
                        label += (
                            f"{arg_label}, " if i != len(arg.args) - 1 else arg_label
                        )
                label += ")"
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

    def __source(self):
        self.statements.extend(
            [
                Statement(
                    NodeData(
                        _id=1,
                        _type=NodeType.ASSIGN,
                        label="x.1 = 0",
                    )
                ),
                Statement(
                    NodeData(
                        _id=2,
                        _type=NodeType.ASSIGN,
                        label="y.1 = 20",
                    )
                ),
                Statement(
                    NodeData(
                        _id=3,
                        _type=NodeType.ASSIGN,
                        label="y.2 = φ(y.1, y.3)",
                    )
                ),
                WhileStatement(
                    NodeData(
                        _id=4,
                        _type=NodeType.IF,
                        label="y.2 > 0",
                    ),
                    body=[
                        Statement(
                            NodeData(
                                _id=5,
                                _type=NodeType.ASSIGN,
                                label="x.2 = φ(x.1, x.3)",
                            )
                        ),
                        WhileStatement(
                            NodeData(
                                _id=6,
                                _type=NodeType.IF,
                                label="x.2 < 10",
                            ),
                            body=[
                                Statement(
                                    NodeData(
                                        _id=7,
                                        _type=NodeType.ASSIGN,
                                        label="c.1 = x.2 + y.2",
                                    )
                                ),
                                Statement(
                                    NodeData(
                                        _id=8,
                                        _type=NodeType.ASSIGN,
                                        label="print(c.1)",
                                    )
                                ),
                                Statement(
                                    NodeData(
                                        _id=9,
                                        _type=NodeType.ASSIGN,
                                        label="x.3 = x.2 + 1",
                                    )
                                ),
                            ],
                        ),
                        Statement(
                            NodeData(
                                _id=10,
                                _type=NodeType.ASSIGN,
                                label="y.3 = y.2 + 1",
                            )
                        ),
                    ],
                ),
            ]
        )
        self.counter = 10
        self.__append_end()
