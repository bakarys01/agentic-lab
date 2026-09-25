"""Real-browser checks against the served API with a deterministic concierge."""

import threading
from pathlib import Path
from socket import socket
from time import sleep

import pytest
import uvicorn
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from backend.api import create_api_app


class BrowserConcierge:
    def answer_query_with_metadata(self, query):
        if query == "Trigger failure":
            raise RuntimeError("private upstream details")
        return {
            "answer": f"Received: {query}\nPolicy and research response. <script>bad()</script>",
            "agents_used": ["policy", "research"],
            "latency_ms": 125,
        }

    def get_health(self):
        return {"status": "ok", "services": {
            name: {"status": "available"} for name in ("concierge", "policy", "research")
        }}


@pytest.fixture(scope="module")
def browser_app():
    sock = socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_api_app(BrowserConcierge()), log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        sleep(.05)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,900")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    cached = list((Path.home() / ".cache/selenium/chromedriver").glob("**/chromedriver.exe"))
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(str(sorted(cached)[-1])) if cached else Service(), options=options)
        yield driver, f"http://127.0.0.1:{port}"
    finally:
        if driver:
            driver.quit()
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()


def test_browser_question_reaches_concierge_and_renders_safely(browser_app):
    driver, url = browser_app
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: "connected" in d.find_element(By.ID, "connection-status").text.lower())
    driver.find_element(By.CSS_SELECTOR, ".action-pill").click()
    question = driver.find_element(By.ID, "medical-input").get_attribute("value")
    assert "insurance policy" in question
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    wait.until(lambda d: "Received:" in d.find_element(By.ID, "result-text").text)
    answer = driver.find_element(By.ID, "result-text")
    assert question in answer.text
    assert "<script>bad()</script>" in answer.text
    assert not answer.find_elements(By.TAG_NAME, "script")
    assert "policy, research" in driver.find_element(By.ID, "result-meta").get_attribute("textContent")
    assert driver.find_element(By.CSS_SELECTOR, "button[type=submit]").is_enabled()
    assert not [log for log in driver.get_log("browser") if log["level"] == "SEVERE" and "favicon" not in log["message"]]


def test_browser_failure_recovers_and_mobile_does_not_overflow(browser_app):
    driver, url = browser_app
    driver.set_window_size(375, 812)
    driver.get(url)
    field = driver.find_element(By.ID, "medical-input")
    field.send_keys("Trigger failure")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: "unavailable" in d.find_element(By.ID, "result-text").text)
    assert "private" not in driver.find_element(By.ID, "result-text").text
    field.clear()
    field.send_keys("x" * 1000)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    wait.until(lambda d: "Received:" in d.find_element(By.ID, "result-text").text)
    assert driver.execute_script("return document.documentElement.scrollWidth <= window.innerWidth")
    driver.find_element(By.CSS_SELECTOR, ".action-pill").click()
    assert "insurance policy" in field.get_attribute("value")


def test_chat_layout_has_one_focus_border_and_preserves_turns(browser_app):
    driver, url = browser_app
    driver.set_window_size(1280, 900)
    driver.get(url)
    field = driver.find_element(By.ID, "medical-input")
    field.click()
    assert field.value_of_css_property("outline-style") == "none"
    wait = WebDriverWait(driver, 15)
    for question in ["First question", "Second question"]:
        field.send_keys(question)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        wait.until(lambda d: question in d.find_element(By.ID, "result-text").text)
        assert field.get_attribute("value") == ""
    users = driver.find_elements(By.CSS_SELECTOR, ".user-message")
    assert [row.find_element(By.CSS_SELECTOR, ".message-text").text for row in users] == ["First question", "Second question"]
    archive = driver.find_element(By.CSS_SELECTOR, ".assistant-message")
    assert "First question" in archive.text
    assert "Second question" in driver.find_element(By.ID, "result-text").text
    assert users[0].rect["x"] > archive.rect["x"]
    active = driver.find_element(By.ID, "chat-result")
    assert field.rect["y"] > active.rect["y"]
    assert len(driver.find_elements(By.ID, "result-text")) == 1


def test_compact_status_and_versioned_assets(browser_app):
    driver, url = browser_app
    driver.get(url)
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_element(By.ID, 'check-connection').get_attribute('data-state') == 'connected')
    assert driver.find_element(By.ID, 'connection-status').text == 'Connected'
    assert '?v=' in driver.find_element(By.CSS_SELECTOR, 'script[src]').get_attribute('src')
    assert '?v=' in driver.find_element(By.CSS_SELECTOR, 'link[rel=stylesheet]').get_attribute('href')
    assert not driver.find_elements(By.ID, 'question-help')
    assert len(driver.find_elements(By.CSS_SELECTOR, '.action-pill')) == 3
