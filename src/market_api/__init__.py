"""Market - MineOS App market API Interface."""

# Programmed by CoolCat467
# Partially ported from
# https://github.com/IgorTimofeev/MineOS/blob/master/Applications/App%20Market.app/Main.lua

from __future__ import annotations

# Market - MineOS App market API Interface
# Copyright (C) 2024  CoolCat467
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__title__ = "App Market API Interface"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"


from enum import IntEnum
from typing import TYPE_CHECKING, Any, Final, NamedTuple

from market_api import lua_parser

if TYPE_CHECKING:
    from collections.abc import Iterable

    import httpx

# HOST: Final = "http://mineos.modder.pw/MineOSAPI/2.04/"
HOST: Final = "http://mineos.buttex.ru/MineOSAPI/2.04/"
##AGENT: Final = (
##    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36"
##)
AGENT = "CoolCat Market Client"

## Known script names:
# verify : token -> html page
# delete : token, file_id
# change_password : email, current_password, new_password
# review : token, file_id, rating, comment
# update : token, file_id, name, source_url, path, description, category_id, license_id
# upload : token,          name, source_url, path, description, category_id, license_id
# dialogs : token
# message : token, user_name, text
# messages: token, user_name
# review_vote: token, review_id, rating (0 (not helpful)|1 (yes helpful))
# download: token, file_id

# publication : file_id, language_id
# statistics : None
# reviews: file_id, [offset, count]
# login : email or name, password
# register : name, email, password
# publications : Optional: category_id, order_by, order_direction, offset, count, search, file_ids

LICENSES: Final = {
    1: "MIT",
    2: "GNU GPLv3",
    3: "GNU AGPLv3",
    4: "GNU LGPLv3",
    5: "Apache Licence 2.0",
    6: "Mozilla Public License 2.0",
    7: "The Unlicense",
}

ORDER_BY: Final = ("popularity", "rating", "name", "date")


class PUBLICATION_CATEGORY(IntEnum):  # noqa: N801
    """Publication category enums."""

    Applications = 1
    Libraries = 2
    Scripts = 3
    Wallpapers = 4


class PUBLICATION_LANGUAGE(IntEnum):  # noqa: N801
    """Publication language enums.

    Used in `get_publication` for localization-dependant strings.
    """

    English = 18
    Russian = 71


class FileType(IntEnum):
    """Publication dependency file type enums."""

    MAIN = 1
    RESOURCE = 2
    ICON = 3
    LOCALIZATION = 4
    PREVIEW = 5


def get_url(script: str) -> str:
    """Return URL of script."""
    return f"{HOST}{script}.php"


class APIError(Exception):
    """Market API Error Exception."""

    __slots__ = ()


async def api_request(
    client: httpx.AsyncClient,
    script: str,
    post: dict[str, Any] | None = None,
    html_raise_exception: bool = True,
) -> dict[str, object]:
    """Request data from script with MineOS App Market API.

    Raises APIError in the event the requested script fails.

    If received an html page, if html_raise_exception is set returns
    html data as {"html": <content>} instead of raising an APIError
    exception.
    """
    # Headers here may not be required but just in case we send the same
    # headers MineOS itself sends.
    headers = {
        "User-Agent": AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Send post request to script endpoint
    response = await client.post(get_url(script), data=post, headers=headers)

    text = response.text
    # See if returned response might be an html page
    if "<html>" in text:
        # If flag set, return html page data instead of exception
        if not html_raise_exception:
            return {"html": text}
        title = text
        # Find title
        if "<title>" in text and "</title>" in text:
            start = text.index("<title>")
            end = text.index("</title>")
            title = text[start + 7 : end]
        raise APIError(f'Got HTML page "{title}", not MineOS data')

    # Parse
    table = lua_parser.parse_lua_table(text)
    assert isinstance(table, dict)

    if not table.get("success", True):
        table["reason"] = table.get(
            "reason",
            "<no reason returned by marketplace API>",
        )
        raise APIError(table["reason"])
    return table


class Statistics(NamedTuple):
    """Marketplace Statistics Result Data."""

    users_count: int
    publications_count: int
    reviews_count: int
    messages_count: int
    last_registered_user: str
    most_popular_user: str


async def get_statistics(client: httpx.AsyncClient) -> Statistics:
    """Return marketplace statistics data."""
    response = await api_request(client, "statistics")
    assert isinstance(response["result"], dict)
    return Statistics(**response["result"])


async def change_password(
    client: httpx.AsyncClient,
    email: str,
    current_password: str,
    new_password: str,
) -> dict[str, object]:
    """Change password given email, current password, and new password."""
    return await api_request(
        client,
        "change_password",
        {
            "email": email,
            "current_password": current_password,
            "new_password": new_password,
        },
    )


class LoginData(NamedTuple):
    """Login Data returned by `login`."""

    id: int
    token: str
    name: str
    email: str
    is_verified: bool
    timestamp: int


async def login(
    client: httpx.AsyncClient,
    password: str,
    name: str | None = None,
    email: str | None = None,
) -> LoginData:
    """Return login data (including token) from credentials.

    Requires [username or email] and password.
    """
    request = {"password": password}

    if name is not None:
        request.update({"name": name})
    if email is not None:
        request.update({"email": email})

    response = await api_request(
        client,
        "login",
        request,
    )
    assert isinstance(response["result"], dict)
    return LoginData(**response["result"])


class SearchPublication(NamedTuple):
    """Partial Publication data returned from search endpoint."""

    file_id: int
    publication_name: str
    user_name: str
    version: int | float
    category_id: int
    reviews_count: int
    downloads: int

    icon_url: str = ""

    average_rating: float | None = None
    popularity: float | None = None


async def get_publications(
    client: httpx.AsyncClient,
    category_id: PUBLICATION_CATEGORY | None = None,
    order_by: str | None = None,
    order_direction: str | None = None,
    offset: int | None = None,
    count: int = 100,
    search: str | None = None,
    file_ids: list[int] | None = None,
) -> list[SearchPublication]:
    """Return a list of publication data from search.

    None of the arguments except client are required.

    Category ID should be one of the PUBLICATION_CATEGORY values.

    Offset is an offset in where to start returning search data from
    so you can see more than just the top 100 publications.

    Count controls how many publications you get back.
    Counts greater than 100 don't seem to have any effect.

    Search allows you to search all publications.

    File IDs allow you to get back specific publications
    Note that these values are not the full results you can get from
    `get_publication`.
    """
    request: dict[str, str | int | list[int]] = {"count": count}

    if category_id is not None:
        request.update({"category_id": category_id})
    if order_by is not None:
        request.update({"order_by": order_by})
    if order_direction is not None:
        request.update({"order_direction": order_direction})
    if offset is not None:
        request.update({"offset": offset})
    if search is not None:
        request.update({"search": search})
    if file_ids is not None:
        request.update({"file_ids": file_ids})

    response = await api_request(
        client,
        "publications",
        request,
    )
    results = response["result"]
    assert isinstance(results, list)
    return [SearchPublication(**obj) for obj in results]


async def get_all_publications(
    client: httpx.AsyncClient,
    category_id: PUBLICATION_CATEGORY,
    per_request: int = 100,
) -> dict[int, SearchPublication]:
    """Return a dictionary mapping publication ids to publication objects.

    For `per_request`, see `get_publications`'s `count` argument.

    Returns all results in the entire marketplace for a given category.
    """
    all_items: dict[int, SearchPublication] = {}
    page = 0
    while True:
        publications = await get_publications(
            client,
            category_id=category_id,
            offset=page * per_request,
            count=per_request,
        )

        if not publications:
            break
        for publication in publications:
            all_items[publication.file_id] = publication
        page += 1
    return all_items


class Dependency(NamedTuple):
    """Dependency item from Publication."""

    source_url: str
    path: str
    version: int | float
    type_id: FileType
    publication_name: str | None = None
    category_id: int | None = None


class Publication(NamedTuple):
    """Full publication object that the `publication` endpoint gives us."""

    file_id: int
    publication_name: str
    user_name: str
    version: int | float
    category_id: int

    source_url: str
    path: str
    license_id: int
    timestamp: int
    initial_description: str
    translated_description: str
    dependencies_data: dict[int, Dependency]

    dependencies: list[int] | None = None
    all_dependencies: list[int] | None = None

    icon_url: str | None = None

    average_rating: float = 0
    whats_new: str | None = None
    whats_new_version: float | None = None
    downloads: int = 0


async def get_publication(
    client: httpx.AsyncClient,
    file_id: int,
    language_id: int,
) -> Publication:
    """Return Publication object associated with given file id."""
    response = await api_request(
        client,
        "publication",
        {"file_id": file_id, "language_id": language_id},
    )
    result = response["result"]
    assert isinstance(result, dict)
    result.update(
        {
            "dependencies_data": {
                k: Dependency(**v)
                for k, v in result.get("dependencies_data", {}).items()
            },
        },
    )
    return Publication(**result)


async def update_publication(
    client: httpx.AsyncClient,
    token: str,
    file_id: int,
    name: str,
    source_url: str,
    path: str,
    description: str,
    license_id: int,
    category_id: PUBLICATION_CATEGORY,
    dependencies: list[int] | None = None,
    whats_new: str | None = None,
) -> dict[str, object]:
    """Update a publication that account associated with token owns.

    license_id should be one of LICENSES.

    dependencies should be a list of file ids required for the new
    publication to function.
    """
    if dependencies is None:
        dependencies = []

    request = {
        "token": token,
        "file_id": file_id,
        "name": name,
        "source_url": source_url,
        "path": path,
        "description": description,
        "license_id": license_id,
        "category_id": category_id,
        "dependencies": dependencies,
    }

    if whats_new is not None:
        request.update({"whats_new": whats_new})

    return await api_request(
        client,
        "update",
        request,
    )


async def upload_publication(
    client: httpx.AsyncClient,
    token: str,
    name: str,
    source_url: str,
    path: str,
    description: str,
    license_id: int,
    category_id: PUBLICATION_CATEGORY,
    dependencies: list[int] | None = None,
    whats_new: str | None = None,
) -> dict[str, object]:
    """Upload a new publication for account associated with token.

    license_id should be one of LICENSES.

    dependencies should be a list of file ids required for the new
    publication to function.
    """
    if dependencies is None:
        dependencies = []

    request = {
        "token": token,
        "name": name,
        "source_url": source_url,
        "path": path,
        "description": description,
        "license_id": license_id,
        "category_id": category_id,
        "dependencies": dependencies,
    }

    if whats_new is not None:
        request.update({"whats_new": whats_new})

    return await api_request(
        client,
        "upload",
        request,
    )


async def delete_publication(
    client: httpx.AsyncClient,
    token: str,
    file_id: int,
) -> dict[str, object]:
    """Delete a publication that account associated with token owns."""
    return await api_request(
        client,
        "delete",
        {"token": token, "file_id": file_id},
    )


class Notification(NamedTuple):
    """Notification object from `dialogs` endpoint."""

    dialog_user_name: str
    timestamp: int
    text: str
    last_message_is_read: bool
    last_message_user_name: str
    last_message_user_id: int


async def get_notifications(
    client: httpx.AsyncClient,
    token: str,
) -> list[Notification]:
    """Return notifications from account associated with token."""
    response = await api_request(
        client,
        "dialogs",
        {
            "token": token,
        },
    )
    assert isinstance(response["result"], list)
    return [Notification(**obj) for obj in response["result"]]


async def message_user(
    client: httpx.AsyncClient,
    token: str,
    user_name: str,
    text: str,
) -> None:
    """Send message to user_name from account associated with token."""
    await api_request(
        client,
        "message",
        {
            "token": token,
            "user_name": user_name,
            "text": text,
        },
    )


class Message(NamedTuple):
    """Message object."""

    text: str
    user_name: str
    timestamp: int


async def read_messages_from_user(
    client: httpx.AsyncClient,
    token: str,
    user_name: str,
) -> list[Message]:
    """Read messages from user_name to account associated with token."""
    response = await api_request(
        client,
        "messages",
        {
            "token": token,
            "user_name": user_name,
        },
    )
    assert isinstance(response["result"], list)
    return [Message(**obj) for obj in response["result"]]


class ReviewVotes(NamedTuple):
    """Review votes data."""

    total: int = 0
    positive: int = 0

    @property
    def negative(self) -> int:
        """Total count minus positive count."""
        return self.total - self.positive


class Review(NamedTuple):
    """Review response object from `reviews` endpoint."""

    id: int
    user_name: str
    rating: int
    comment: str
    timestamp: int
    votes: ReviewVotes


async def get_reviews(
    client: httpx.AsyncClient,
    publication_file_id: int,
    offset: int = 0,
    count: int | None = None,
) -> list[Review]:
    """Return list of reviews."""
    args = {"file_id": publication_file_id}
    if offset:
        args["offset"] = offset
    if count:
        args["count"] = count
    response = await api_request(
        client,
        "reviews",
        args,
    )
    assert isinstance(response["result"], list)

    reviews = []
    for obj in response["result"]:
        obj["votes"] = ReviewVotes(**obj.get("votes", {}))
        reviews.append(Review(**obj))

    return reviews


async def post_review(
    client: httpx.AsyncClient,
    token: str,
    file_id: int,
    rating: int,
    comment: str,
) -> None:
    """Post review from account associated with token.

    Rating should be in the range of 1 to 5 inclusive where
    1 is worst and 5 is greatest.
    """
    await api_request(
        client,
        "review",
        {
            "token": token,
            "file_id": file_id,
            "rating": rating,
            "comment": comment,
        },
    )


async def vote_review_helpful(
    client: httpx.AsyncClient,
    token: str,
    review_id: int,
    helpful: bool,
) -> str:
    """Vote if a review is helpful or not.

    Return response text.
    """
    response = await api_request(
        client,
        "review_vote",
        {
            "token": token,
            "review_id": review_id,
            "rating": helpful,
        },
    )
    value = response.get("result", "<No response>")
    assert isinstance(value, str)
    return value


async def mark_downloaded(
    client: httpx.AsyncClient,
    token: str,
    file_id: int,
) -> dict[str, bool]:
    """Send telemetry signal that you downloaded a publication.

    Return if updated server's record for this user's token.

    Official client records all downloads since Jul 4, 2024, 9:27 AM CDT.
    """
    response = await api_request(
        client,
        "download",
        {
            "token": token,
            "file_id": file_id,
        },
    )
    assert "result" in response
    value = response["result"]
    assert isinstance(value, dict)
    return value


def indent(level: int, text: str) -> str:
    """Indent text by level of spaces."""
    prefix = " " * level
    return "\n".join(prefix + line for line in text.splitlines())


def pretty_format_response(
    response: dict[str, Any] | list[Any] | set[Any] | tuple[Any, ...],
) -> str:
    """Pretty format response data."""

    def print_named_tuple(
        result: Iterable[object],
        field_names: tuple[str, ...],
    ) -> str:
        fields = []
        for field, obj in zip(field_names, result, strict=False):
            fields.append(f"{field} = {print_value(obj)}")
        value = ",\n".join(fields)
        return f"(\n{indent(2, value)}\n)"

    def print_list(result: Iterable[Any]) -> str:
        if not result:
            return "[]"
        if hasattr(result, "_fields"):
            return print_named_tuple(result, result._fields)
        value = ",\n".join(map(print_value, result))
        return f"[\n{indent(2, value)}\n]"

    def print_dict(result: dict[object, object]) -> str:
        if not result:
            return "{}"
        formatted = {print_value(k): print_value(v) for k, v in result.items()}
        value = ",\n".join(f"{k}: {v}" for k, v in formatted.items())
        return f"{{\n{indent(2, value)}\n}}"

    def print_value(result: object) -> str:
        if isinstance(result, list | tuple | set):
            return print_list(result)
        if isinstance(result, dict):
            return print_dict(result)
        if isinstance(result, str | int | float | None):
            return repr(result)
        raise NotImplementedError(type(result))

    return print_value(response)


def pretty_print_response(
    response: dict[str, Any] | list[Any] | set[Any] | tuple[Any, ...],
) -> None:
    """Pretty print response data."""
    print(pretty_format_response(response))


if __name__ == "__main__":
    print(f"{__title__} v{__version__}\nProgrammed by {__author__}.\n")
