"""Get Publication Example."""

# Programmed by CoolCat467

from __future__ import annotations

# Get Publication Example

__title__ = "Get Publication Example"
__author__ = "CoolCat467"
__license__ = "MIT"

import httpx
import trio
from market_api import (
    PUBLICATION_LANGUAGE,
    get_publication,
    get_reviews,
    get_statistics,
    pretty_print_response,
)


async def async_run() -> None:
    """Run async."""
    # Create httpx client
    async with httpx.AsyncClient(timeout=15) as client:  # http2 = True
        file_id = 1936
        # Get publication number and print it out nicely
        pretty_print_response(
            await get_publication(
                client,
                file_id=file_id,
                language_id=PUBLICATION_LANGUAGE.English,
            ),
        )

        # Print out market statistics
        pretty_print_response(await get_statistics(client))

        # Print out reviews for publication number 1936
        pretty_print_response(await get_reviews(client, file_id))


def run() -> None:
    """Run example."""
    trio.run(async_run, strict_exception_groups=True)


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
