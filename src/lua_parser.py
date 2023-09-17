"""Lua parser."""

# Programmed by CoolCat467

from __future__ import annotations

__title__ = "Lua parser"
__author__ = "CoolCat467"
__version__ = "0.0.0"


import re
from collections.abc import Collection
from typing import Any, Generic, NamedTuple, NoReturn, TypeVar, cast


class ParseError(Exception):
    """Raised on any type comment parse error.

    The 'comment' attribute contains the comment that produced the error.
    """

    def __init__(self, comment: str | None = None) -> None:
        """Initialize with comment."""
        if comment is None:
            comment = ""
        super().__init__(comment)


class Token(NamedTuple):
    """Base token."""

    text: str
    line: int
    column: int


class Identifier(Token):
    """A lua identifier, such as a variable name."""

    __slots__ = ()


class Operator(Token):
    """Base class for all operator tokens."""

    __slots__ = ()


class Assignment(Operator):
    """A lua assignment operator."""

    __slots__ = ()


class Literal(Token):
    """Base literal."""

    __slots__ = ()


class StrLit(Literal):
    """String literal."""

    __slots__ = ()


class Numeric(Literal):
    """Numeric literal."""

    __slots__ = ()


class Comment(Token):
    """An entire comment line."""

    __slots__ = ()


class Separator(Token):
    """A separator or punctuator token such as braces or quotes."""

    __slots__ = ()


class End(Token):
    """A token representing the end."""

    __slots__ = ()


KEYWORDS = {
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
    "false",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "nil",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "true",
    "until",
    "while",
}

IDENTIFIER = re.compile(r"^[a-z_][a-z_\d]*", re.IGNORECASE)
COMMENT = re.compile("--.*\n")
##INTEGER = re.compile('^[\d]+')
NUMERIC = re.compile(r"^(\d+)(\.\d+)?(e(?:-|\+)?\d+)?")
HEXADECIMAL = re.compile(
    r"(0x[a-f\d]+)(\.[a-f\d]+)?(p(?:-|\+)?\d+)?",
    re.IGNORECASE,
)


def tokenize(text: str) -> list[Token]:
    """Tokenize lua code."""
    line = 1
    column = 0

    tokens: list[Token] = []
    while True:
        read = 1
        last_line = line
        token: Token | None = End

        if not text:
            read = 0
        elif text[0] in {" ", "\r", "\t"}:
            token = None
        elif text[0] == "\n":
            token = None
            line += 1
        elif text[0] in "()[]{},":
            token = Separator
        elif text.startswith("--"):
            match_ = COMMENT.match(text)
            if not match_:
                raise ParseError(f"Could not parse comment from {text!r}")

            token = Comment
            read = match_.end() - 1
        elif text[0] == "=":
            token = Assignment
        elif text[0] in {'"', "'"}:
            read = 1
            start_bracket = text[0]
            while read < len(text):
                char = text[read]
                if char == start_bracket and text[read - 1] != "\\":
                    read += 1
                    break
                read += 1

            token = StrLit
        else:
            if match_ := (HEXADECIMAL.match(text) or NUMERIC.match(text)):
                tokens.append(
                    Numeric(
                        "$".join(x or "" for x in match_.groups()),
                        line,
                        column,
                    ),
                )

                token = None
                read = match_.end()
            elif match_ := IDENTIFIER.match(text):
                token = Identifier
                read = match_.end()
            else:
                print(f"{tokens = }")
                raise ParseError(f"Could not parse {text!r}")

        if last_line != line:
            column = 0
        else:
            column += read

        if token is not None:
            tokens.append(token(text[:read], line, column))
            if issubclass(token, End):
                return tokens
        text = text[read:]


T = TypeVar("T")


class Value(Generic[T]):
    """A type value, potentially collection of multiple."""

    __slots__ = ("name", "args")

    def __init__(
        self,
        name: str,
        *args: T,
    ) -> None:
        """Set up name and arguments."""
        self.name = name
        if args:
            self.args = tuple(args)
        else:
            self.args = ()

    def __repr__(self) -> str:
        """Return representation of self."""
        args = f", {self.args!r}" if self.args else ""
        return f"{self.__class__.__name__}({self.name!r}{args})"

    def __str__(self) -> str:
        """Return type value representation of self."""
        args = tuple(map(str, self.args))
        if not args:
            if self.name:
                return self.name
            return "[]"
        values = ", ".join(args)
        return f"{self.name}[{values}]"

    def __eq__(self, rhs: object) -> bool:
        """Return if rhs is equal to self."""
        if isinstance(rhs, self.__class__):
            return self.name == rhs.name and self.args == rhs.args
        return super().__eq__(rhs)

    def unpack(self) -> tuple[T | tuple[object, ...], ...]:
        """Unpack all arguments."""
        args: list[T | tuple[object, ...]] = []
        for arg in self.args:
            if not isinstance(arg, Value):
                args.append(arg)
                continue
            args.append(arg.unpack())
        return tuple(args)

    def unpack_join(self) -> tuple[object | tuple[object, ...], ...]:
        """Unpack all arguments and simplify single argument values."""
        args: list[object | tuple[object, ...]] = []
        for arg in self.args:
            if not isinstance(arg, Value):
                args.append(arg)
                continue
            result = arg.unpack_join()
            if len(result) == 1:
                args.extend(result)
            else:
                args.append(result)
        return tuple(args)


def list_or(values: Collection[str]) -> str:
    """Return comma separated listing of values joined with ` or `."""
    if len(values) <= 2:
        return " or ".join(values)
    copy = list(values)
    copy[-1] = f"or {copy[-1]}"
    return ", ".join(copy)


class Parser:
    """Implementation of the type comment parser."""

    __slots__ = ("tokens", "i")

    def __init__(self, tokens: list[Token]) -> None:
        """Initialize with tokens list."""
        self.tokens = tokens
        self.i = 0

    def fail(self, error: str | None) -> NoReturn:
        """Raise parse error."""
        raise ParseError(error)

    def peek(self) -> Token:
        """Peek at next token."""
        if self.i >= len(self.tokens):
            self.fail("Ran out of tokens")
        return self.tokens[self.i]

    def lookup(self) -> str:
        """Peek at next token and return it's text."""
        return self.peek().text
        ##if value is None:
        ##    return "None"

    def next(self) -> Token:  # noqa: A003
        """Get next token."""
        token = self.peek()
        self.i += 1
        return token

    def back(self) -> None:
        """Go back one token."""
        self.i -= 1

    def rest_tokens(self) -> list[Token]:
        """Return all tokens not processed."""
        return self.tokens[self.i : len(self.tokens)]

    def __repr__(self) -> str:
        """Return representation of self."""
        return f"{self.__class__.__name__}({self.rest_tokens()!r})"

    def expect(self, text: str) -> None:
        """Expect next token text to be text."""
        got = self.next().text
        if got != text:
            self.fail(f"Expected {text!r}, got {got!r}")

    def expect_type(
        self,
        token_type: type[Token] | tuple[type[Token], ...],
    ) -> Token:
        """Expect next token to be instance of token_type. Return token."""
        token = self.next()
        if not isinstance(token, token_type):
            if isinstance(token_type, tuple):
                expect_str = list_or(
                    [f"{cls.__name__!r}" for cls in token_type],
                )
            else:
                expect_str = f"{token_type.__name__!r}"
            self.fail(f"Expected {expect_str}, got {token!r}")
        return token

    def parse_string_literal(self) -> Value[str]:
        """Parse a string literal."""
        token = self.expect_type(StrLit)
        # Read the string literal character by character and look for
        # escape sequences like \a, \n, \t, etc.
        value = ""
        skip = 0  # Number of chars to not add to running value
        for idx, char in enumerate(token.text):
            if skip:
                skip -= 1
                continue
            if char != "\\":
                value += char
                continue
            # Is escape sequence start, so read next char to find which one
            value += token.text[idx + 1].translate(
                {
                    97: "\a",
                    98: "\b",
                    102: "\f",
                    110: "\n",
                    114: "\r",
                    116: "\t",
                    118: "\v",
                    92: "\\",
                },
            )
            skip = 1
        return Value("String", value)

    def parse_numeric_literal(self) -> Value[int | float]:
        """Parse a numeric literal."""
        token = self.expect_type(Numeric)

        decimal, fractional, exponent = token.text.split("$")
        text = "".join((decimal, fractional, exponent))

        is_float = fractional or exponent

        value: int | float
        if decimal.lower().startswith("0x"):  # is hex?
            value = float.fromhex(text) if is_float else int(text, 16)
            return Value("Float" if is_float else "Integer", value)
        value = float(text) if is_float else int(text)
        return Value("Float" if is_float else "Integer", value)

    def parse_field(self) -> Value[str | Value[object]]:
        """Parse table field."""
        if self.lookup() == "[":
            self.expect("[")
            value = self.parse_value()
            self.expect("]")
            self.expect_type(Assignment)
            return Value("Field", value, self.parse_value())
        if isinstance(self.peek(), Identifier):
            return self.parse_identifier()
        return Value("Indexed", self.parse_value())

    def parse_table(self) -> Value[object]:
        """Parse table."""
        self.expect("{")
        fields = []
        while self.lookup() != "}":
            fields.append(self.parse_field())

            while string := self.lookup():
                if string in {",", ";"}:
                    self.expect(string)
                else:
                    break
        self.expect("}")
        return Value("Table", *fields)

    def parse_identifier(self) -> Value[object]:
        """Parse identifier."""
        identifier = self.expect_type(Identifier)
        text = identifier.text
        if text in {"true", "false"}:
            return Value("Boolean", text == "true")
        if text in KEYWORDS:
            return Value("Keyword", text)
        self.expect_type(Assignment)
        return Value(
            "Assignment",
            Value("Identifier", text),
            self.parse_value(),
        )

    def parse_value(self) -> Value[Any]:
        """Parse value."""
        if isinstance(self.peek(), StrLit):
            return self.parse_string_literal()
        if isinstance(self.peek(), Numeric):
            return self.parse_numeric_literal()
        if isinstance(self.peek(), Identifier):
            return self.parse_identifier()
        if self.lookup() == "{":
            return self.parse_table()
        raise NotImplementedError(self.peek())


def parse_lua_table(text: str) -> object:
    """Parse lua table from lua source."""
    tokens = tokenize(text)
    # print(f'{tokens = }')
    parser = Parser(tokens)
    value = parser.parse_value()
    # print(value)

    def read_value(value: Value[str | Value[object]]) -> object:
        """Read value base function."""
        assert isinstance(value, Value)
        if value.name in {
            "String",
            "Boolean",
            "Float",
            "Integer",
            "Identifier",
        }:
            return value.args[0]
        if value.name == "Table":
            return read_table(cast(Value[Value[object]], value))
        if value.name == "Assignment":
            return read_assignment(value)
        raise NotImplementedError(value.name)

    def read_assignment(
        value: Value[Value[str | Value[object]]],
    ) -> tuple[str, object]:
        """Read an Assignment value."""
        assert value.name == "Assignment"
        key, data = value.args
        return (read_value(key), read_value(data))

    def read_field(
        value: Value[object],
        table: dict[str | int, object],
    ) -> tuple[tuple[str | int, object], bool]:
        """Read a table field value."""
        assert value.name in {"Field", "Assignment", "Indexed"}
        if value.name == "Assignment":
            return read_assignment(value), False
        if value.name == "Indexed":
            return (len(table), read_value(value.args[0])), True
        if value.name == "Field":
            field, field_value = value.args
            return (read_value(field), read_value(field_value)), False
        raise NotImplementedError(value.name)

    def read_table(
        value: Value[Value[object]],
    ) -> dict[str | int, object] | list[object]:
        """Read a table and all of it's fields."""
        assert value.name == "Table"
        table: dict[str | int, object] = {}
        all_indexed = True
        for field in value.args:
            pair, indexed = read_field(field, table)
            if not indexed:
                all_indexed = False
            key, store_value = pair
            table[key] = store_value
        if all_indexed:
            return [table[i] for i in range(len(table))]
        return table

    return read_value(value)
    # return value.unpack_join()


def run() -> None:
    """Run test of module."""
    tokens = tokenize(
        """ a = 'alo\\n123"'
 a = "alo\\n123\\""
 a = '\\97lo\\10\\04923"'
 c = 0X1.921FB54442D18P+1
 j = 314.16e-2
 e = 0xBEBADA""",
    )
    ##print(f'{tokens = }')
    parser = Parser(tokens)
    for _ in range(6):
        print(repr(parser.parse_identifier()))

    print(
        parse_lua_table(
            """{
    help = "Help",
    helpInfo = {
        "• Every model consists of shapes. Their count depends of server properties, but by default it's 24 per one model",
        "• Model also can have 2 states: passive and active. If you place printed model in minecraft world and perform a click on it, model will change it's state to the opposite. Shape count is limited to both states",
        "• Hold left mouse button to place first point of shape by X and Y. Drag mouse to resize shape. Use mouse wheel to change Z coordinate. Release button to finish shape editing",
        "• Press right mouse button to select shape under cursor",
        "• Scroll toolbar to show other options",
    },
    file = "File",
    new = "New",
    open = "Open",
    save = "Save",
    saveAs = "Save as",
    disabled = "Disabled",
    enabled = "Enabled",
    add = "Add",
    remove = "Remove",
    rotate = "Rotate",
    flip = "Flip",
    color = "C",
    offset = "Offset",
    scale = "Scale",
    projectorEnabled = "Enabled",
    xAxis = "X-axis",
    yAxis = "Y-axis",
    zAxis = "Z-axis",
    lightLevel = "Light level",
    emitRedstone = "Emit redstone",
    collidable = "Collision",
    buttonMode = "Button mode",
    label = "Label",
    tooltip = "Tooltip",
    tintEnabled = "Use tint",
    tintColor = "Tint color",
    texture = "Texture",
    print = "Print",
    blockSettings = "Model properties",
    projectorSettings = "Projector properties",
    elementSettings = "Shape properties",
    failedToPrint = "Failed to print",
}""",
        ),
    )

    print(
        parse_lua_table(
            """{
    winds = {
        [0] = "N",
        [1] = "NE",
        [2] = "E",
        [3] = "SE",
        [4] = "S",
        [5] = "SW",
        [6] = "W",
        [7] = "NW",
        [8] = "N",
    },
    mmHg = " mm Hg",
    speed = " m/s, ",
    population = "Population: ",
    city = "Type city name here",
    cityError = "Wrong result. Check city name and try again."
}""",
        ),
    )


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
