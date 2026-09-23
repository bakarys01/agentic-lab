from smolagents import Tool, tool
import math
from typing import Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

@tool
def suggest_menu(occasion: str) -> str:
    """
    Suggests a menu based on the occasion.
    Args:
        occasion: The type of occasion for the party.
    """
    if occasion == "casual":
        return "Pizza, snacks, and drinks."
    elif occasion == "formal":
        return "3-course dinner with wine and dessert."
    elif occasion == "superhero":
        return "Buffet with high-energy and healthy food."
    else:
        return "Custom menu for the butler."

@tool
def catering_service_tool(query: str) -> str:
    """
    This tool returns the highest-rated catering service in Gotham City.
    
    Args:
        query: A search term for finding catering services.
    """
    # Example list of catering services and their ratings
    services = {
        "Gotham Catering Co.": 4.9,
        "Wayne Manor Catering": 4.8,
        "Gotham City Events": 4.7,
    }
    
    # Find the highest rated catering service (simulating search query filtering)
    best_service = max(services, key=services.get)
    
    return best_service

class SuperheroPartyThemeTool(Tool):
    name = "superhero_party_theme_generator"
    description = """
    This tool suggests creative superhero-themed party ideas based on a category.
    It returns a unique party theme idea."""
    
    inputs = {
        "category": {
            "type": "string",
            "description": "The type of superhero party (e.g., 'classic heroes', 'villain masquerade', 'futuristic Gotham').",
        }
    }
    
    output_type = "string"

    def forward(self, category: str):
        themes = {
            "classic heroes": "Justice League Gala: Guests come dressed as their favorite DC heroes with themed cocktails like 'The Kryptonite Punch'.",
            "villain masquerade": "Gotham Rogues' Ball: A mysterious masquerade where guests dress as classic Batman villains.",
            "futuristic gotham": "Neo-Gotham Night: A cyberpunk-style party inspired by Batman Beyond, with neon decorations and futuristic gadgets."
        }
        
        return themes.get(category.lower(), "Themed party idea not found. Try 'classic heroes', 'villain masquerade', or 'futuristic Gotham'.")


@tool
def calculate_cargo_travel_time(
    origin_coords: Tuple[float, float],
    destination_coords: Tuple[float, float],
    cruising_speed_kmh: Optional[float] = 750.0,  # Average speed for cargo planes
) -> float:
    """
    Calculate the travel time for a cargo plane between two points on Earth using great-circle distance.

    Args:
        origin_coords: Tuple of (latitude, longitude) for the starting point
        destination_coords: Tuple of (latitude, longitude) for the destination
        cruising_speed_kmh: Optional cruising speed in km/h (defaults to 750 km/h for typical cargo planes)

    Returns:
        float: The estimated travel time in hours

    Example:
        >>> # Chicago (41.8781° N, 87.6298° W) to Sydney (33.8688° S, 151.2093° E)
        >>> result = calculate_cargo_travel_time((41.8781, -87.6298), (-33.8688, 151.2093))
    """

    def to_radians(degrees: float) -> float:
        return degrees * (math.pi / 180)

    # Extract coordinates
    lat1, lon1 = map(to_radians, origin_coords)
    lat2, lon2 = map(to_radians, destination_coords)

    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371.0

    # Calculate great-circle distance using the haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    distance = EARTH_RADIUS_KM * c

    # Add 10% to account for non-direct routes and air traffic controls
    actual_distance = distance * 1.1

    # Calculate flight time
    # Add 1 hour for takeoff and landing procedures
    flight_time = (actual_distance / cruising_speed_kmh) + 1.0

    # Format the results
    return round(flight_time, 2)


import helium

from smolagents import tool
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


def get_driver():
    """Returns the Selenium driver currently managed by Helium."""
    driver = helium.get_driver()

    if driver is None:
        raise RuntimeError(
            "No active browser found. Start a browser with Helium first."
        )

    return driver


@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """
    Searches for text on the current page and jumps to the nth occurrence.

    Args:
        text: The text to search for.
        nth_result: Which occurrence to jump to (default: 1).
    """
    driver = get_driver()

    elements = driver.find_elements(
        By.XPATH,
        f"//*[contains(text(), '{text}')]"
    )

    if not elements:
        raise Exception(f"No matches found for '{text}'.")

    if nth_result < 1 or nth_result > len(elements):
        raise Exception(
            f"Match n°{nth_result} not found "
            f"(only {len(elements)} matches found)."
        )

    elem = elements[nth_result - 1]

    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        elem,
    )

    return (
        f"Found {len(elements)} matches for '{text}'. "
        f"Focused on element {nth_result} of {len(elements)}."
    )


@tool
def go_back() -> None:
    """Goes back to the previous page."""
    driver = get_driver()
    driver.back()


@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up by pressing Escape.
    This does not necessarily close cookie consent banners.
    """
    driver = get_driver()

    ActionChains(driver).send_keys(Keys.ESCAPE).perform()

    return "Pressed Escape to close the visible popup."

#---------------------------------------------------------------------------------

from pathlib import Path

import pymupdf

POLICY_PATH = Path("data/2026AnthemgHIPSBC.pdf")


def _load_policy() -> list[dict]:
    """Load the policy once and preserve page numbers."""
    doc = pymupdf.open(POLICY_PATH)

    return [
        {
            "page": page_number,
            "text": page.get_text(),
        }
        for page_number, page in enumerate(doc, start=1)
    ]


POLICY_PAGES = _load_policy()


@tool
def search_policy(query: str) -> str:
    """
    Search the health insurance policy for passages relevant to a query.

    Args:
        query: What to search for in the insurance policy.
    """

    query_terms = set(query.lower().split())

    scored_pages = []

    for page in POLICY_PAGES:
        text = page["text"]
        text_lower = text.lower()

        score = sum(term in text_lower for term in query_terms)

        if score > 0:
            scored_pages.append(
                (score, page["page"], text)
            )

    scored_pages.sort(reverse=True)

    if not scored_pages:
        return "No relevant information found in the policy."

    results = []

    for _, page_number, text in scored_pages[:3]:
        results.append(
            f"""
SOURCE: Insurance Policy
PAGE: {page_number}

{text[:5000]}
"""
        )

    return "\n\n".join(results)