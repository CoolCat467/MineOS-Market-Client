#!/usr/bin/env python3

"""Download App."""

# Programmed by CoolCat467

from __future__ import annotations

# Download App
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

__title__ = "Download App"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"

import re

import httpx
import trio
from market_api import (
    PUBLICATION_LANGUAGE,
    Dependency,
    Publication,
    get_publication,
)


def fs_remove_slashes(path: str) -> str:
    """Remove extra slashes from path."""
    return "/".join(x for x in path.split("/") if x)


def fs_path(path: str) -> str:
    """Return path but remove file from end if exists."""
    if not path.endswith("/"):
        return path.rsplit("/", 1)[0]
    return path


APP_PATH_REGEX = re.compile(r"\.[awlp]+\/+Main\.lua")


def get_application_path_from_version(versions_path: str) -> str:
    """Return application path."""
    if APP_PATH_REGEX.match(versions_path):
        return fs_path(versions_path)
    return versions_path


DOWNLOAD_PATHS = {
    1: "Applications/",
    2: "Libraries/",
    3: "",
    4: "Wallpapers/",
}


def get_dependancy_path(main_file_path: str, dependency: Dependency) -> str:
    """Return dependency path."""
    # If is publication
    if dependency.publication_name:
        path = DOWNLOAD_PATHS[dependency.category_id] + dependency.path
    else:  # Is resource
        # Absolute path
        if dependency.path.startswith("/"):
            path = dependency.path
        else:
            # Relative path
            path = (
                get_application_path_from_version(main_file_path)
                + "/"
                + dependency.path
            )
    return fs_remove_slashes(path)


MK_FILES_LOCK = trio.Lock()


async def download_mineos(
    client: httpx.AsyncClient,
    url: str,
    path: str,
) -> None:
    """Download contents of url and save to given path inside `mineos` folder."""
    path = await trio.Path("mineos").joinpath(*path.split("/")).absolute()
    async with MK_FILES_LOCK:
        if not await path.parent.exists():
            await path.parent.mkdir(parents=True)
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    async with await path.open("wb") as file:
        await file.write(await response.aread())
    await response.aclose()


async def download_publication(
    client: httpx.AsyncClient,
    publication: Publication,
) -> None:
    """Download all files and dependencies from publication."""
    main_file_path = publication.publication_name
    if not main_file_path and publication.category_id in {1, 4}:
        main_file_path = "Main.lua"

    await download_mineos(
        client,
        publication.source_url,
        main_file_path + f"/{publication.path}",
    )

    if publication.dependencies:
        async with trio.open_nursery() as nursery:
            for depencency_id in publication.all_dependencies:
                dependency = publication.dependencies_data[depencency_id]

                dependency_path = get_dependancy_path(
                    main_file_path,
                    dependency,
                )

                nursery.start_soon(
                    download_mineos,
                    client,
                    dependency.source_url,
                    dependency_path,
                )


async def async_run() -> None:
    """Run async."""
    path = await trio.Path("mineos").absolute()
    consent = (
        input(
            f"Making sure, it is ok for us to download files to {path}? (y/N): ",
        ).lower()
        == "y"
    )
    if not consent:
        print("Exiting.")
        return

    print("Good example file ID is `106`")
    file_id = int(input("Input Publication ID to download: "))

    print("\nDownloading Publication Manifest...")
    # Create httpx client
    async with httpx.AsyncClient() as client:  # http2 = True
        # Retrieve publication
        publication = await get_publication(
            client,
            file_id,
            PUBLICATION_LANGUAGE.English,
        )
        print(
            "\nPublication Manifest download complete.\nDownloading files...",
        )
        await download_publication(client, publication)
    print("\nPublication download complete.")


def run() -> None:
    """Run example."""
    trio.run(async_run, strict_exception_groups=True)


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
