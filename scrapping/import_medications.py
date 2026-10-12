"""Download a bounded BDPM sample and load it into the medication database."""

import argparse
import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.request import Request, urlopen


SOURCE_PAGE = "https://base-donnees-publique.medicaments.gouv.fr/telechargement"
SOURCE_BASE = "https://base-donnees-publique.medicaments.gouv.fr/download/file/"
FILES = ("CIS_bdpm.txt", "CIS_CIP_bdpm.txt", "CIS_COMPO_bdpm.txt")
MAX_FILE_BYTES = 20_000_000


@dataclass(frozen=True)
class SelectedRecords:
    medications: tuple[tuple[str, ...], ...]
    presentations: tuple[tuple[str, ...], ...]
    compositions: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class SourceFile:
    name: str
    text: str
    updated_on: date
    sha256: str

    @property
    def url(self) -> str:
        return SOURCE_BASE + self.name


def parse_source_date(page: str, filename: str) -> date:
    """Read the date printed beside one file link on the official download page."""
    link = re.search(
        r'href=["\']/download/file/' + re.escape(filename) + r'["\'][^>]*>(.*?)</a>',
        page,
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = re.search(
        r'Date de mise à jour\s*:\s*(\d{2}/\d{2}/\d{4})',
        link.group(1),
        flags=re.IGNORECASE,
    ) if link else None
    if match is None:
        raise ValueError(f"Missing official update date for {filename}")
    return datetime.strptime(match.group(1), "%d/%m/%Y").date()


def _rows(text: str, minimum_columns: int, filename: str) -> tuple[tuple[str, ...], ...]:
    rows = []
    for number, row in enumerate(csv.reader(io.StringIO(text), delimiter="\t"), 1):
        if not row:
            continue
        if len(row) < minimum_columns or not row[0].strip().isdigit():
            raise ValueError(f"Invalid {filename} row {number}")
        rows.append(tuple(value.strip() for value in row))
    return tuple(rows)


def select_records(
    specialties_text: str,
    presentations_text: str,
    compositions_text: str,
    limit: int,
) -> SelectedRecords:
    """Select stable CIS codes and retain all their related source rows."""
    if limit < 1:
        raise ValueError("limit must be positive")

    medications = _rows(specialties_text, 7, FILES[0])
    presentations = _rows(presentations_text, 7, FILES[1])
    compositions = _rows(compositions_text, 8, FILES[2])
    presentation_cis = {row[0] for row in presentations}
    composition_cis = {row[0] for row in compositions}
    eligible = [
        row for row in medications
        if row[0] in presentation_cis and row[0] in composition_cis
    ]
    if len(eligible) < limit:
        raise ValueError(f"Only {len(eligible)} medications available for limit {limit}")

    chosen = sorted(
        eligible,
        key=lambda row: (hashlib.sha256(row[0].encode("ascii")).digest(), row[0]),
    )[:limit]
    cis = {row[0] for row in chosen}
    return SelectedRecords(
        medications=tuple(sorted(chosen, key=lambda row: row[0])),
        presentations=tuple(row for row in presentations if row[0] in cis),
        compositions=tuple(row for row in compositions if row[0] in cis),
    )


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "MediNova-BDPM-import/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = response.read(MAX_FILE_BYTES + 1)
    if not payload or len(payload) > MAX_FILE_BYTES:
        raise ValueError(f"Unexpected download size for {url}")
    return payload


def download_sources() -> dict[str, SourceFile]:
    page = _download(SOURCE_PAGE).decode("utf-8")
    sources = {}
    for name in FILES:
        payload = _download(SOURCE_BASE + name)
        sources[name] = SourceFile(
            name=name,
            # The presentations file is UTF-8; the other BDPM exports use cp1252.
            text=payload.decode("utf-8" if name == "CIS_CIP_bdpm.txt" else "cp1252"),
            updated_on=parse_source_date(page, name),
            sha256=hashlib.sha256(payload).hexdigest(),
        )
    return sources


def _optional(value: str) -> str | None:
    return value or None


def import_records(sources: dict[str, SourceFile], selected: SelectedRecords) -> None:
    """Atomically replace only the previous BDPM sample in PostgreSQL."""
    import psycopg

    with psycopg.connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM medications WHERE source_import_id IN "
            "(SELECT id FROM medication_imports WHERE source_name = ANY(%s))",
            (list(FILES),),
        )
        cursor.execute(
            "DELETE FROM medication_imports WHERE source_name = ANY(%s)",
            (list(FILES),),
        )
        ids = {}
        for name in FILES:
            source = sources[name]
            cursor.execute(
                "INSERT INTO medication_imports "
                "(source_name, source_url, source_updated_on, source_sha256) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (name, source.url, source.updated_on, source.sha256),
            )
            ids[name] = cursor.fetchone()[0]

        cursor.executemany(
            "INSERT INTO medications "
            "(cis, name, pharmaceutical_form, administration_routes, "
            "authorization_status, commercialization_status, source_import_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (row[0], row[1], _optional(row[2]), _optional(row[3]),
                 _optional(row[4]), _optional(row[6]), ids[FILES[0]])
                for row in selected.medications
            ],
        )
        cursor.executemany(
            "INSERT INTO medication_presentations "
            "(cis, cip7, cip13, label, administrative_status, "
            "commercialization_status, source_import_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (row[0], _optional(row[1]), _optional(row[6]), row[2],
                 _optional(row[3]), _optional(row[4]), ids[FILES[1]])
                for row in selected.presentations
            ],
        )
        cursor.executemany(
            "INSERT INTO medication_compositions "
            "(cis, pharmaceutical_element, substance_code, substance_name, "
            "substance_dosage, dosage_reference, component_nature, "
            "linkage_number, source_import_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (row[0], _optional(row[1]), _optional(row[2]), row[3],
                 _optional(row[4]), _optional(row[5]), _optional(row[6]),
                 _optional(row[7]), ids[FILES[2]])
                for row in selected.compositions
            ],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import an official BDPM sample")
    parser.add_argument("--limit", type=int, default=500, help="Number of specialties")
    args = parser.parse_args()

    sources = download_sources()
    selected = select_records(
        sources[FILES[0]].text,
        sources[FILES[1]].text,
        sources[FILES[2]].text,
        args.limit,
    )
    import_records(sources, selected)
    print(
        f"Imported {len(selected.medications)} medications, "
        f"{len(selected.presentations)} presentations and "
        f"{len(selected.compositions)} compositions from BDPM."
    )


if __name__ == "__main__":
    main()
