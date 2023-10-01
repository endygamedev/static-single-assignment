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


class BreakStatement(Statement):
    pass


@dataclass
class ContinueStatement(Statement):
    condition: NodeData


ConditionStatement = TypeVar("ConditionStatement", IfStatement, WhileStatement)
