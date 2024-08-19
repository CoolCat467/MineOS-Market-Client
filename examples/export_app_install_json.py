#!/usr/bin/env python3

"""Export App Install Details as JSON."""

# Programmed by CoolCat467

from __future__ import annotations

# Export App Install Details as JSON
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

__title__ = "Export App Install Details as JSON"
__author__ = "CoolCat467"
__version__ = "0.0.0"
__license__ = "GNU General Public License Version 3"

import json
import os
from typing import Any

import httpx
import trio

from market_api import (
    PUBLICATION_LANGUAGE,
    APIError,
    Publication,
    get_publication,
)


def named_tuple_to_dict(tuple_: tuple[object, ...]) -> dict[str, object]:
    """Convert named tuple to dictionary."""
    if not hasattr(tuple_, "_asdict"):
        raise ValueError("Must be NamedDict instance")
    return tuple_._asdict()


async def retrieve_details(
    client: httpx.AsyncClient,
    file_id: int,
    language_id: PUBLICATION_LANGUAGE = PUBLICATION_LANGUAGE.English,
) -> dict[int, Publication]:
    """Retrieve details of given file id and all dependencies of this publication."""
    # Get publication data
    publication = await get_publication(
        client,
        file_id=file_id,
        language_id=language_id,
    )

    # Collecting all manifests
    files: dict[int, Publication] = {}
    files[file_id] = publication

    # Discover dependencies
    deps = set()
    if publication.dependencies:
        deps |= set(publication.dependencies)
    if publication.all_dependencies:
        deps |= set(publication.dependencies)

    async def retrieve_dep(dep_id: int) -> None:
        """Handle retrieving one depencancy."""
        try:
            # Recursive download all required for this dependency
            details = await retrieve_details(
                client,
                dep_id,
                language_id,
            )
            # Add on to existing list
            files.update(details)
        except APIError:
            # If dependency does not exist, should be given in
            # publication's `dependencies_data` section.
            files[dependancy_id] = publication.dependencies_data[dependancy_id]

    # Start retrieving all dependencies at the same time
    async with trio.open_nursery() as nursery:
        for dependancy_id in sorted(deps):
            nursery.start_soon(retrieve_dep, dependancy_id)

    return files


def manifest_to_dict(
    manifest: dict[str, Publication],
) -> dict[str, dict[str, object]]:
    """Convert dict of named tuples to dict of dicts."""
    new: dict[str, Any] = {}
    for key, value in manifest.items():
        new[key] = named_tuple_to_dict(value)
    return new


async def async_run() -> None:
    """Run async."""
    print("Good example file ID is `1936`")
    file_id = int(input("Input File ID to save manifest of: "))

    print("\nDownloading Manifest...")
    # Create httpx client
    async with httpx.AsyncClient(timeout=15) as client:  # http2 = True
        # Retrieve manifests
        all_manifests = await retrieve_details(
            client,
            file_id=file_id,
            language_id=PUBLICATION_LANGUAGE.English,
        )
        # Convert to dictionaries so JSON encoder is helpful
        manifest = manifest_to_dict(all_manifests)

    print("\nManifest download complete.")

    filename = input(f"\nSave file in {os.getcwd()!r} as given filename: ")

    # Add .json if no extension given
    if "." not in filename:
        filename += ".json"

    # Get absolute save path
    path = await trio.Path(filename).absolute()

    # Write JSON data to file
    async with await path.open("w", encoding="utf-8") as file_handle:
        await file_handle.write(json.dumps(manifest, sort_keys=True))
    print(f"\nSaved manifest to {filename!r}.")


def run() -> None:
    """Run example."""
    trio.run(async_run, strict_exception_groups=True)


if __name__ == "__main__":
    print(f"{__title__}\nProgrammed by {__author__}.\n")
    run()
