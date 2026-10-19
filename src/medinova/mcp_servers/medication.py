"""Search the structured BDPM sample through an MCP tool."""

import json
import re

import psycopg
from medinova.mcp_servers.traced_server import TracedFastMCP
from psycopg.rows import dict_row


mcp = TracedFastMCP("medication_catalog")
MAX_RESULTS = 5


@mcp.tool()
def get_medication(query: str) -> str:
    """Find medications by name, CIS, CIP7 or CIP13.

    Returns matching specialties with their presentations and compositions.
    The catalog is a bounded BDPM sample, so no match does not prove that a
    medication does not exist in the full public database.
    """
    raw_term = query.strip()
    if not 1 <= len(raw_term) <= 100:
        raise ValueError("Provide a medication query of 1 to 100 characters.")

    code = re.search(r"\b(?:CIS|CIP7?|CIP13)\s*[:#-]?\s*(\d{7,13})\b", raw_term, re.I)
    term = code.group(1) if code else raw_term

    # Escape LIKE wildcards so the supplied name is searched literally.
    name_pattern = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    with psycopg.connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            "SELECT m.cis, m.name, m.pharmaceutical_form, m.administration_routes, "
            "m.authorization_status, m.commercialization_status "
            "FROM medications m "
            "WHERE m.cis = %s OR m.name ILIKE %s ESCAPE '\\' "
            "OR EXISTS (SELECT 1 FROM medication_presentations p "
            "WHERE p.cis = m.cis AND (p.cip7 = %s OR p.cip13 = %s)) "
            "ORDER BY CASE WHEN m.cis = %s THEN 0 ELSE 1 END, m.name, m.cis "
            "LIMIT %s",
            (term, name_pattern, term, term, term, MAX_RESULTS),
        )
        matches = []
        for medication in cursor.fetchall():
            cursor.execute(
                "SELECT cip7, cip13, label, administrative_status, commercialization_status "
                "FROM medication_presentations WHERE cis = %s ORDER BY cip13, cip7",
                (medication["cis"],),
            )
            presentations = cursor.fetchall()
            cursor.execute(
                "SELECT pharmaceutical_element, substance_code, substance_name, "
                "substance_dosage, dosage_reference, component_nature, linkage_number "
                "FROM medication_compositions WHERE cis = %s ORDER BY id",
                (medication["cis"],),
            )
            compositions = cursor.fetchall()
            matches.append({
                **medication,
                "presentations": presentations,
                "compositions": compositions,
            })

    return json.dumps({"medications": matches}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
