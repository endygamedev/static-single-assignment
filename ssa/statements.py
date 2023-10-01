from dataclasses import dataclass, field
from typing import TypeVar

from .builder import NodeData

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


class ContinueStatement(Statement):
    pass


ConditionStatement = TypeVar("ConditionStatement", IfStatement, WhileStatement)
