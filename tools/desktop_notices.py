"""Add project notices and directions for obtaining the matching game source."""
from pathlib import Path
from zipfile import ZipFile


def add_notices(archive: ZipFile, root: Path, release: str, prefix: str = "") -> None:
    for name in ("LICENSE", "MEDIA.md"):
        archive.write(root / name, prefix + name)

    source_name = f"NightNine-{release}-source.zip"
    archive.writestr(
        prefix + "SOURCE.txt",
        f"Night Nine {release} corresponding source\n\n"
        f"Download {source_name} free of charge from the same release page "
        "or folder where you obtained this game. Extract the archive and "
        "open its README.md for the project and build instructions.\n\n"
        "Please keep the matching source available to recipients when "
        "redistributing these binaries. See LICENSE for the full terms "
        "and MEDIA.md for the scope of the project and media licenses.\n",
    )
