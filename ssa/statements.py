from dataclasses import dataclass, field
from typing import TypeVar
from enum import Enum, auto


class NodeType(Enum):
    NULL = auto()
    START = auto()
    ASSIGN = auto()
    IF = auto()
    BREAK = auto()
    CONTINUE = auto()
    FUNCTION_DEF = auto()
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


@dataclass
class BreakStatement(Statement):
    while_statement: Statement


@dataclass
class ContinueStatement(Statement):
    while_statement: Statement


@dataclass
class FunctionStatement(Statement):
    body: list[Statement] = field(default_factory=list)
    last_function_node: NodeData | None = None


ConditionStatement = TypeVar("ConditionStatement", IfStatement, WhileStatement)
