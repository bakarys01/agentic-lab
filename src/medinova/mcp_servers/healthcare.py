import json

from medinova.mcp_servers.traced_server import TracedFastMCP

from medinova.paths import PROJECT_ROOT


mcp = TracedFastMCP("doctorserver")

DOCTORS_FILE = PROJECT_ROOT / "data" / "doctors.json"

with DOCTORS_FILE.open("r", encoding="utf-8") as file:
    doctors: list[dict] = json.load(file)


@mcp.tool()
def list_doctors(
    state: str | None = None,
    city: str | None = None,
    specialty: str | None = None,
) -> str:
    """Return doctors matching a location and/or specialty.

    Args:
        state: State or region, such as "TX" or "Île-de-France".
        city: City, such as "Paris".
        specialty: Medical specialty, such as "Psychiatry".

    Returns:
        JSON containing matching doctors or a missing-criteria error.
    """
    target_state = (state or "").strip().casefold()
    target_city = (city or "").strip().casefold()
    target_specialty = (specialty or "").strip().casefold()

    if not any((target_state, target_city, target_specialty)):
        return json.dumps({
            "error": "Provide at least one criterion: state, city, or specialty."
        })

    results = [
        doctor
        for doctor in doctors
        if (
            not target_state
            or doctor["address"]["state"].casefold() == target_state
        )
        and (
            not target_city
            or doctor["address"]["city"].casefold() == target_city
        )
        and (
            not target_specialty
            or doctor["specialty"].casefold() == target_specialty
        )
    ]

    return json.dumps(results, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
