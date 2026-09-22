from io import BytesIO
from time import sleep

import helium
from PIL import Image

from smolagents import (
    CodeAgent,
    DuckDuckGoSearchTool,
    OpenAIServerModel,
)
from smolagents.memory import ActionStep

from tools.my_tools import (
    go_back,
    close_popups,
    search_item_ctrl_f,
)

def save_screenshot(step_log: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)

    driver = helium.get_driver()

    if driver is None:
        return

    current_step = step_log.step_number

    # Remove previous screenshots to keep memory smaller
    for previous_step in agent.memory.steps:
        if (
            isinstance(previous_step, ActionStep)
            and previous_step.step_number is not None
            and current_step is not None
            and previous_step.step_number <= current_step - 2
        ):
            previous_step.observations_images = None

    # Capture current browser
    png_bytes = driver.get_screenshot_as_png()
    image = Image.open(BytesIO(png_bytes))

    print(f"Captured browser screenshot: {image.size} pixels")

    step_log.observations_images = [image.copy()]

    # Store current URL
    url_info = f"Current url: {driver.current_url}"

    step_log.observations = (
        url_info
        if step_log.observations is None
        else step_log.observations + "\n" + url_info
    )

helium_instructions = """
You can use `helium` to interact with the browser.

The browser is already open.

Use Helium for browser interactions:
- `helium.go_to(url)` to navigate.
- `helium.click(text)` to click.
- `helium.write(text, into=...)` to enter text.
- `helium.press(...)` to press keys.
- `helium.scroll_down(...)` to scroll.

Do not create a new browser or WebDriver instance.
Use the existing browser session managed by Helium.
"""


model = OpenAIServerModel(model_id="gpt-4o")

agent = CodeAgent(
    tools=[
        DuckDuckGoSearchTool(),
        go_back,
        close_popups,
        search_item_ctrl_f,
    ],
    model=model,
    additional_authorized_imports=["helium"],
    step_callbacks=[save_screenshot],
    max_steps=20,
    verbosity_level=2,
)


# IMPORTANT: actually create the browser
helium.start_chrome(
    "https://www.google.com",
    headless=False,
)

try:
    agent.run(
        """
I am Alfred, the butler of Wayne Manor, responsible for verifying
the identity of guests at party.

Please search for images of Wonder Woman and generate a detailed
visual description based on those images.

Additionally, navigate to Wikipedia to gather key details about
her appearance.
"""
        + helium_instructions
    )

finally:
    helium.kill_browser()