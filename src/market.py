"""Market - MineOS App market API test."""

# Programmed by CoolCat467

__title__ = "App market API test"
__author__ = "CoolCat467"
__version__ = "0.0.0"

from typing import Any, Final, cast

import convert
import httpx
import lua_parser
import trio

# HOST: Final = "http://mineos.modder.pw/MineOSAPI/2.04/"
HOST: Final = "http://mineos.buttex.ru/MineOSAPI/2.04/"
##AGENT: Final = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36"
AGENT: Final = "App market API test"

## Known script names:
# delete : token, file_id
# change_password : email, current_password, new_password
# message : token, user_name, text
# review : token, file_id, rating, comment
# update : token, file_id, name, source_url, path, description, category_id, license_id
# upload : token, name, source_url, path, description, category_id, license_id

# publication : file_id, language_id
# statistics : None
# login : email or name, password
# register : name, email, password
# publications : Optional: category_id, order_by, order_direction, offset, count, search, file_ids

LICENSES: Final = (
    "MIT",
    "GNU GPLv3",
    "GNU AGPLv3",
    "GNU LGPLv3",
    "Apache Licence 2.0",
    "Mozilla Public License 2.0",
    "The Unlicense",
)

ORDER_BY: Final = ("popularity", "rating", "name", "date")

CATEGORIES: Final = {"Applications": 1, "Libraries": 2, "Scripts": 3}


def get_url(script: str) -> str:
    """Return URL of script."""
    return f"{HOST}{script}.php"


async def api_request(
    client: httpx.AsyncClient,
    script: str,
    post: dict[str, int] | None = None,
) -> dict[str, object]:
    """Request data from script with MineOS App Market API."""
    headers = {"User-Agent": AGENT}

    response = await client.post(get_url(script), data=post, headers=headers)

    text = convert.split_squished(response.text)
    # print(text)
    if "<html>" in text:
        title = "<unknown title>"
        if "<title>" in text and "</title>" in text:
            start = text.index("<title>")
            end = text.index("</title>")
            title = text[start + 7 : end]
        raise ConnectionError(f'Got HTML page "{title}", not MineOS data')
    ##    try:
    ##        return convert.lang_to_json(text)[0]
    ##    except JSONDecodeError:
    ##        print(f'{text = }')
    ##        raise
    try:
        table = lua_parser.parse_lua_table(text)
        if not table.get("success", True):
            table["reason"] = table.get("reason", "").translate(
                {10: "", 9: ""},
            )
        return table
    except Exception:
        print(f"{text = }")
        raise


async def get_statistics(client: httpx.AsyncClient) -> dict[str, Any]:
    """Get statistics."""
    response = await api_request(client, "statistics")
    return cast(dict[str, Any], response["result"])


async def get_publications(
    client: httpx.AsyncClient,
    category: str = "Applications",
    per_request: int = 100,
) -> dict[int, dict[str, Any]]:
    """Get publications."""
    all_items = {}
    page = 0
    while True:
        response = await api_request(
            client,
            "publications",
            {
                "category_id": CATEGORIES[category],
                "offset": page * per_request,
                "count": per_request,
            },
        )
        # print(response)
        results = response["result"]
        if not results:
            break
        # print(results)
        for k, v in results.items():
            all_items[int(k)] = v
        page += 1
    return all_items


async def async_run() -> None:
    """Run async."""
    async with httpx.AsyncClient() as client:  # http2 = True
        ##test = await api_request(
        ##    client,
        ##    'publications',
        ##    {'order_direction': 'dec'}
        ##)
        pubs = await get_publications(client)
        for _number, pub in pubs.items():
            print(f'{pub["file_id"]}: {pub["publication_name"]}')
        print("\n")
        print(
            await api_request(
                client,
                "publication",
                {"file_id": 1609, "language_id": 2},
            ),
        )
        print(await api_request(client, "statistics"))
        ##print(await api_request(client, "login"))


def run() -> None:
    """Run test of module."""
    trio.run(async_run)


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.")
    run()
