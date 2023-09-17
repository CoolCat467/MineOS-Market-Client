"""Lua parser."""

# Programmed by CoolCat467

from __future__ import annotations

__title__ = "Lua parser"
__author__ = "CoolCat467"
__version__ = "0.0.0"


import re
from collections import deque
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

    @property
    def endcolumn(self) -> int:
        """End column number."""
        return self.column + len(self.text)

    @property
    def endline(self) -> int:
        """End line number."""
        return self.line + self.text.count("\n")


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
    column = -1

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
        elif text[0] in "()[]{},;":
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
                token = Numeric
                read = match_.end()
            elif match_ := IDENTIFIER.match(text):
                token = Identifier
                read = match_.end()
            else:
                print(f"{tokens = }")
                raise ParseError(f"Could not parse {text!r}")

        if last_line != line:
            column = -1
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
        if not self.args:
            return self.name or "[]"
        args = []
        for arg in self.args:
            if isinstance(arg, Value):
                args.append(str(arg))
            else:
                args.append(repr(arg))
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

    __slots__ = ("tokens", "i", "next_indexed_field")

    def __init__(self, tokens: list[Token]) -> None:
        """Initialize with tokens list."""
        self.tokens = tokens
        self.i = 0
        self.next_indexed_field: deque[int] = deque()

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

    def expect_or(self, options: Collection[str]) -> Token:
        """Expect next token text to be text. Return the token we got."""
        token = self.next()
        if token.text not in options:
            self.fail(
                f"Expected {list_or([repr(x) for x in options])}, got {token.text!r}",
            )
        return token

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
        return Value("String", value[1:-1])

    def parse_numeric_literal(self) -> Value[int | float]:
        """Parse a numeric literal."""
        token = self.expect_type(Numeric)

        text = token.text
        match_ = HEXADECIMAL.match(text) or NUMERIC.match(text)
        decimal, fractional, exponent = match_.groups()

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
        index = self.next_indexed_field.pop()
        self.next_indexed_field.append(index + 1)
        # return Value("Indexed", self.parse_value())
        return Value("Field", Value("Integer", index), self.parse_value())

    def parse_table(self) -> Value[object]:
        """Parse table."""
        self.expect("{")
        self.next_indexed_field.append(1)
        fields = []
        while self.lookup() != "}":
            fields.append(self.parse_field())

            if self.expect_or({",", ";", "}"}).text == "}":
                self.back()
        self.next_indexed_field.pop()
        self.expect("}")
        return Value("Table", *fields)

    def parse_function_arguments(self) -> list[Value[object]]:
        """Parse function call arguments."""
        self.expect("(")
        arguments = []
        while self.lookup() != ")":
            arguments.append(self.parse_value())

            if self.expect_or({",", ")"}).text == ")":
                self.back()
        self.expect(")")
        return arguments

    def parse_identifier(self) -> Value[object]:
        """Parse identifier."""
        identifier = self.expect_type(Identifier)
        text = identifier.text
        if text in {"true", "false"}:
            return Value("Boolean", text == "true")
        if text in KEYWORDS:
            return Value("Keyword", text)
        # Function calls are strange.
        if self.lookup() == "(":  # Regular function call
            return Value(
                "FunctionCall",
                Value("Identifier", text),
                Value("Arguments", *self.parse_function_arguments()),
            )
        if self.lookup() == "{":  # syntactic sugar call from table constructor
            return Value(
                "FunctionCall",
                Value("Identifier", text),
                Value("Arguments", *self.parse_table()),
            )
        if isinstance(
            self.peek(),
            StrLit,
        ):  # syntactic sugar call from string literal
            return Value(
                "FunctionCall",
                Value("Identifier", text),
                Value("Arguments", *self.parse_string_literal()),
            )
        if isinstance(self.peek(), Assignment):
            self.expect_type(Assignment)
            return Value(
                "Assignment",
                Value("Identifier", text),
                self.parse_value(),
            )
        return Value("Identifier", text)

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


def parse_lua_table(text: str, convert_lists: bool = True) -> object:
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
    ) -> tuple[str | int, object]:
        """Read a table field value."""
        assert value.name in {"Field", "Assignment"}
        if value.name == "Assignment":
            return read_assignment(value)
        # if value.name == "Indexed":
        #    return (str(len(table)), read_value(value.args[0]))
        if value.name == "Field":
            field, field_value = value.args
            return (read_value(field), read_value(field_value))
        raise NotImplementedError(value.name)

    def read_table(
        value: Value[Value[object]],
    ) -> dict[str | int, object] | list[object]:
        """Read a table and all of it's fields."""
        assert value.name == "Table"
        table: dict[str | int, object] = {}

        last_int_key = 0
        convert_list = convert_lists

        for field in value.args:
            key, store_value = read_field(field, table)
            if convert_list:
                if not isinstance(key, int):
                    convert_list = False
                elif key == (last_int_key + 1):
                    last_int_key = key
                else:
                    convert_list = False
            table[key] = store_value
        if not convert_list:
            return table
        return [table[i + 1] for i in range(len(table))]

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
 e = 0xBEBADA
 a = { [f(1)] = g; "x", "y"; x = 1, f(x), [30] = 23; 45 }""",
    )
    # print(f'{tokens = }')
    ##for token in tokens:
    ##    print(token)
    global parser
    parser = Parser(tokens)
    for _ in range(7):
        print(str(parser.parse_identifier()))
    ##
    ##    print(
    ##        parse_lua_table(
    ##            """{
    ##    help = "Help",
    ##    helpInfo = {
    ##        "• Every model consists of shapes. Their count depends of server properties, but by default it's 24 per one model",
    ##        "• Model also can have 2 states: passive and active. If you place printed model in minecraft world and perform a click on it, model will change it's state to the opposite. Shape count is limited to both states",
    ##        "• Hold left mouse button to place first point of shape by X and Y. Drag mouse to resize shape. Use mouse wheel to change Z coordinate. Release button to finish shape editing",
    ##        "• Press right mouse button to select shape under cursor",
    ##        "• Scroll toolbar to show other options",
    ##    },
    ##    file = "File",
    ##    new = "New",
    ##    open = "Open",
    ##    save = "Save",
    ##    saveAs = "Save as",
    ##    disabled = "Disabled",
    ##    enabled = "Enabled",
    ##    add = "Add",
    ##    remove = "Remove",
    ##    rotate = "Rotate",
    ##    flip = "Flip",
    ##    color = "C",
    ##    offset = "Offset",
    ##    scale = "Scale",
    ##    projectorEnabled = "Enabled",
    ##    xAxis = "X-axis",
    ##    yAxis = "Y-axis",
    ##    zAxis = "Z-axis",
    ##    lightLevel = "Light level",
    ##    emitRedstone = "Emit redstone",
    ##    collidable = "Collision",
    ##    buttonMode = "Button mode",
    ##    label = "Label",
    ##    tooltip = "Tooltip",
    ##    tintEnabled = "Use tint",
    ##    tintColor = "Tint color",
    ##    texture = "Texture",
    ##    print = "Print",
    ##    blockSettings = "Model properties",
    ##    projectorSettings = "Projector properties",
    ##    elementSettings = "Shape properties",
    ##    failedToPrint = "Failed to print",
    ##}""",
    ##        ),
    ##    )
    ##
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

    print(
        parse_lua_table(
            """{
    leftBarOffset = 5,

    settingsStyle = "Color scheme",
    settingsAdditional = "Additional properties",

    invalidPassword = "Invalid login or password",
    username = "E-mail or phone number",
    password = "Password",
    login = "Enter",
    twoFactorEnabled = "Use 2FA",
    twoFactor = "2FA code",
    saveLogin = "Save login information:",

    loadCountConversations = "The number of loaded dialogues",
    loadCountMessages = "Number of messages to download",
    loadCountNews = "Number of downloaded news",
    scrollSpeed = "The scroll speed",
    loadCountWall = "Number of posts to download",
    loadCountFriends = "Number of friends to download",
    loadCountDocs = "Number of documents to download",

    profile = "Profile",
    message = "Message",
    sendMessage = "Send message",
    addToFriends = "Add as friend",
    friendRequestSent = "Request has been sent",
    userSubscribedToYou = "Subscribed to you",
    userIsYourFriend = "You have friends",

    profileCounters = {
        { field = "followers", description = " followers" },
        { field = "friends", description = " friends" },
        { field = "photos", description = " photos" },
        { field = "videos", description = " videos" },
        { field = "audios", description = " audio" },
    },
    profileShowAdditional = "Show details",
    profileHideAdditional = "Hide detailed information",
    profileTitleMainInformation = "Basic information",
    profileTitlePersonal = "Life position",
    profileTitleAdditions = "Personal information",
    profileTitleContacts = "Contacts",
    profileKeys = {
        education = "Education",
        inspiredBy = "Inspire",
        relation = "Relations",
        birthday = "Birthday",
        city = "City",
        homeCity = "Hometown",
        languages = "Languages",
        occupation = "Place of work",
        mobilePhone = "Mobile",
        homePhone = "Alt. phone",
        site = "Website",
        activities = "Activity",
        interests = "Interests",
        music = "Favorite music",
        movies = "Favorite movie",
        books = "Favorite book",
        tv = "Favorite show",
        games = "Favorite game",
        quotes = "Favorite quote",
        religion = "Outlook",
        political = "Polit. conviction",
        peopleMain = "People most important",
        lifeMain = "Life most important",
        alcohol = "OTN. for alcohol",
        smoking = "OTN. towards smoking",
    },
    months = {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    },
    relationStatuses = {
        {
            "not married",
            "have a girlfriend",
            "engaged",
            "married",
            "it's complicated",
            "in active search",
            "lover",
            "in civil marriage",
            [0] = "unspecified",
        },
        {
            "not married",
            "have a friend",
            "engaged",
            "married",
            "it's complicated",
            "in active search",
            "lover",
            "in civil marriage",
            [0] = "unspecified",
        }
    },
    personalPoliticalTypes = {
        "Communist",
        "Socialist",
        "Moderate",
        "Liberal",
        "Conservative",
        "Monarchical",
        "Ultraconservative",
        "Indifferent",
        "Libertarian",
    },
    personalPeopleMainTypes = {
        "Intelligence and creativity",
        "Kindness and honesty",
        "Beauty and health",
        "Power and wealth",
        "Courage and perseverance",
        "Humor and love of life",
    },
    personalLifeMainTypes = {
        "Family and children",
        "Career and money",
        "Entertainment and recreation",
        "Science and research",
        "Improving the world",
        "Self-development",
        "Beauty and art",
        "Fame and influence",
    },
    personalBlyadTypes = {
        "Sharply negative",
        "Negative",
        "Compromise",
        "Neutral",
        "Positive",
    },

    friends = "Friends",
    friendsOnline = "Online friends",
    friendsMutual = "Mutual friends",

    news = "Newsfeed",

    send = "Send",
    conversations = "Conversations",
    you = "You: ",
    typeMessageHere = "Write a message...",
    fwdMessages = "Information: ",
    attachments = "Investments: ",
    attachmentsTypes = {
        photo = "photo",
        video = "video",
        audio = "audio",
        doc = "document",
        link = "link",
        market = "goods",
        market_album = "product catalog",
        wall = "record",
        wall_reply = "repost",
        sticker = "sticker",
        gift = "gift",
        audio_message = "audio",
    },
    sentFromMineOS = " (Sent via MineOS VK Client)",

    documents = "Documents",
    documentsCount = "Total documents",
    documentsAdd = "Upload document",

    settings = "Settings",

    exit = "Logout",
}""",
        ),
    )


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
