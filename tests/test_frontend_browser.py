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

from medinova.backend.api import create_api_app


class BrowserConcierge:
    def answer_query_with_metadata(self, query, history=None):
        if query == "Trigger failure":
            raise RuntimeError("private upstream details")
        return {
            "answer": f"Received: {query}\nContext: {history} <script>bad()</script>",
            "agents_used": ["policy", "research"],
            "latency_ms": 125,
        }

    def get_health(self):
        return {"status": "ok", "services": {
            name: {"status": "available"} for name in ("concierge", "policy", "research")
        }}


@pytest.fixture(scope="module")
def browser_app(tmp_path_factory):
    sock = socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_api_app(BrowserConcierge(), db_path=tmp_path_factory.mktemp("browser-db") / "test.sqlite3"), log_level="error"))
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


def register_ui(driver, email):
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_element(By.ID, 'auth-panel').is_displayed())
    if driver.find_element(By.ID, 'auth-title').text != 'Create your account':
        driver.find_element(By.ID, 'auth-toggle').click()
    field = driver.find_element(By.ID, 'auth-email')
    field.clear()
    field.send_keys(email)
    driver.find_element(By.ID, 'auth-password').send_keys('browser-password-123')
    driver.find_element(By.ID, 'auth-submit').click()
    wait.until(lambda d: d.find_element(By.ID, 'chat-workspace').is_displayed())


def submit_question(driver, question):
    field = driver.find_element(By.ID, 'medical-input')
    WebDriverWait(driver, 15).until(lambda d: field.is_enabled())
    field.clear()
    field.send_keys(question)
    driver.find_element(By.CSS_SELECTOR, '#ask-form button[type=submit]').click()
    WebDriverWait(driver, 15).until(lambda d: d.find_element(By.CSS_SELECTOR, '#ask-form button[type=submit]').is_enabled())


def test_browser_register_history_reload_memory_and_delete(browser_app):
    driver, url = browser_app
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'history@example.com')
    submit_question(driver, 'Sleep apnea')
    assert driver.find_element(By.CSS_SELECTOR, '.user-message').is_displayed()
    assert 'Sleep apnea' in driver.find_element(By.CSS_SELECTOR, '.assistant-message').text
    assert not driver.find_elements(By.CSS_SELECTOR, '.assistant-message script')
    driver.refresh()
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.assistant-message')) == 1)
    submit_question(driver, 'Is it covered?')
    assert 'Sleep apnea' in driver.find_elements(By.CSS_SELECTOR, '.assistant-message')[-1].text
    assert len(driver.find_elements(By.CSS_SELECTOR, '.user-message')) == 2
    driver.find_element(By.ID, 'new-conversation').click()
    submit_question(driver, 'Fresh topic')
    assert 'Sleep apnea' not in driver.find_element(By.CSS_SELECTOR, '.assistant-message').text
    assert len(driver.find_elements(By.CSS_SELECTOR, '.conversation-choice')) == 2
    driver.find_element(By.CSS_SELECTOR, '.conversation-actions-toggle').click()
    driver.find_element(By.ID, 'delete-conversation').click()
    driver.switch_to.alert.accept()
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.conversation-choice')) == 1)
    driver.find_element(By.CSS_SELECTOR, '.conversation-choice').click()
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.user-message')) == 2)


def test_browser_rename_and_delete_from_conversation_menu(browser_app):
    driver, url = browser_app
    driver.set_window_size(1280, 900)
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'rename@example.com')
    submit_question(driver, 'Original title')
    driver.find_element(By.CSS_SELECTOR, '.conversation-actions-toggle').click()
    assert driver.find_element(By.ID, 'conversation-menu').is_displayed()
    driver.find_element(By.ID, 'rename-conversation').click()
    name = driver.find_element(By.ID, 'rename-input')
    name.clear()
    name.send_keys('Coverage notes')
    driver.find_element(By.ID, 'rename-save').click()
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, '.conversation-choice').text == 'Coverage notes')
    driver.refresh()
    wait.until(lambda d: d.find_element(By.CSS_SELECTOR, '.conversation-choice').text == 'Coverage notes')
    assert not driver.find_elements(By.CSS_SELECTOR, '.chat-toolbar')
    driver.find_element(By.CSS_SELECTOR, '.conversation-actions-toggle').click()
    driver.find_element(By.ID, 'delete-conversation').click()
    driver.switch_to.alert.accept()
    wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, '.conversation-choice'))


def test_browser_logout_other_account_and_login_restore(browser_app):
    driver, url = browser_app
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'isolation-owner@example.com')
    submit_question(driver, 'Private owner question')
    driver.find_element(By.ID, 'logout').click()
    register_ui(driver, 'other@example.com')
    assert not driver.find_elements(By.CSS_SELECTOR, '.conversation-choice')
    assert not driver.find_elements(By.CSS_SELECTOR, '.user-message')
    driver.find_element(By.ID, 'logout').click()
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_element(By.ID, 'auth-panel').is_displayed())
    if driver.find_element(By.ID, 'auth-title').text != 'Welcome back':
        driver.find_element(By.ID, 'auth-toggle').click()
    driver.find_element(By.ID, 'auth-email').send_keys('isolation-owner@example.com')
    driver.find_element(By.ID, 'auth-password').send_keys('browser-password-123')
    driver.find_element(By.ID, 'auth-submit').click()
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.user-message')) == 1)


def test_browser_failure_retry_and_mobile_focus(browser_app):
    driver, url = browser_app
    driver.set_window_size(375, 812)
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'mobile@example.com')
    driver.find_element(By.ID, 'new-conversation').click()
    submit_question(driver, 'Trigger failure')
    assert 'unavailable' in driver.find_element(By.ID, 'composer-error').text
    submit_question(driver, 'Trigger failure')
    assert len(driver.find_elements(By.CSS_SELECTOR, '.user-message')) == 1
    submit_question(driver, 'x' * 1000)
    assert driver.find_element(By.CSS_SELECTOR, '.assistant-message').is_displayed()
    field = driver.find_element(By.ID, 'medical-input')
    field.click()
    assert field.value_of_css_property('outline-style') == 'none'
    assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')
    assert not driver.find_element(By.ID, 'capabilities').is_displayed()
    composer_bottom = driver.execute_script('return document.querySelector(".composer").getBoundingClientRect().bottom')
    viewport_bottom = driver.execute_script('return window.innerHeight')
    assert viewport_bottom - 60 <= composer_bottom <= viewport_bottom
    driver.find_element(By.ID, 'toggle-history').click()
    assert driver.find_element(By.ID, 'history-panel').is_displayed()
    assert not driver.find_element(By.CSS_SELECTOR, '.sidebar-heading .home-link').is_displayed()
    assert not driver.find_elements(By.ID, 'new-conversation-shortcut')
    assert driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')


def test_composer_stays_at_bottom_while_messages_scroll(browser_app):
    driver, url = browser_app
    driver.set_window_size(1280, 900)
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'composer@example.com')
    assert driver.find_element(By.ID, 'capabilities').is_displayed()
    empty_layout = driver.execute_script('''
        const panel = document.querySelector('.chat-panel').getBoundingClientRect();
        const composer = document.querySelector('.composer').getBoundingClientRect();
        return {panelCenter: (panel.top + panel.bottom) / 2,
                composerCenter: (composer.top + composer.bottom) / 2};
    ''')
    assert abs(empty_layout['composerCenter'] - empty_layout['panelCenter']) < 90
    driver.find_element(By.CSS_SELECTOR, '.action-pill').click()
    assert 'insurance policy' in driver.find_element(By.ID, 'medical-input').get_attribute('value')
    submit_question(driver, 'A detailed question about ' + 'coverage ' * 300)
    assert not driver.find_element(By.ID, 'capabilities').is_displayed()
    layout = driver.execute_script('''
        const composer = document.querySelector('.composer').getBoundingClientRect();
        const messages = document.querySelector('#conversation');
        return {
          composerBottom: composer.bottom,
          viewportBottom: window.innerHeight,
          composerTop: composer.top,
          messagesBottom: messages.getBoundingClientRect().bottom,
          scrollable: messages.scrollHeight > messages.clientHeight,
          atLatestMessage: messages.scrollHeight - messages.clientHeight - messages.scrollTop < 2,
        };
    ''')
    assert layout['viewportBottom'] - 60 <= layout['composerBottom'] <= layout['viewportBottom']
    assert layout['messagesBottom'] <= layout['composerTop']
    assert layout['scrollable']
    assert layout['atLatestMessage']


def test_history_panel_collapses_and_new_conversation_stays_available(browser_app):
    driver, url = browser_app
    driver.set_window_size(1280, 900)
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'sidebar@example.com')
    gutters = driver.execute_script('''
        return {left: document.querySelector('#history-panel').getBoundingClientRect().left,
                right: window.innerWidth - document.querySelector('.chat-panel').getBoundingClientRect().right};
    ''')
    assert 0 <= gutters['left'] <= 32
    assert 0 <= gutters['right'] <= 32
    submit_question(driver, 'What is covered?')
    toggle = driver.find_element(By.ID, 'toggle-history')
    chat = driver.find_element(By.CSS_SELECTOR, '.chat-panel')
    expanded_width = chat.size['width']
    toggle.click()
    assert toggle.get_attribute('aria-expanded') == 'false'
    assert driver.find_element(By.ID, 'history-panel').is_displayed()
    assert not driver.find_element(By.CSS_SELECTOR, '.sidebar-heading .home-link').is_displayed()
    assert chat.size['width'] > expanded_width
    assert not driver.find_elements(By.ID, 'new-conversation-shortcut')
    toggle.click()
    assert toggle.get_attribute('aria-expanded') == 'true'
    assert driver.find_element(By.ID, 'history-panel').is_displayed()
    driver.find_element(By.ID, 'new-conversation').click()
    assert not driver.find_elements(By.CSS_SELECTOR, '.user-message')


def test_compact_status_and_versioned_assets(browser_app):
    driver, url = browser_app
    driver.delete_all_cookies()
    driver.get(url)
    register_ui(driver, 'status@example.com')
    wait = WebDriverWait(driver, 15)
    wait.until(lambda d: d.find_element(By.ID, 'check-connection').get_attribute('data-state') == 'connected')
    assert driver.find_element(By.ID, 'connection-status').text == 'Connected'
    assert driver.execute_script('return document.querySelector("#history-panel").contains(document.querySelector("#account-controls"))')
    assert driver.execute_script('return document.querySelector("#history-panel").contains(document.querySelector("#check-connection"))')
    footer_gap = driver.execute_script('''
        return document.querySelector('#history-panel').getBoundingClientRect().bottom
          - document.querySelector('.sidebar-footer').getBoundingClientRect().bottom;
    ''')
    assert 0 <= footer_gap < 24
    assert driver.execute_script('return document.querySelector("#history-panel").contains(document.querySelector("#toggle-history"))')
    assert driver.find_element(By.ID, 'toggle-history').location['x'] < driver.find_element(By.CSS_SELECTOR, '.sidebar-heading .home-link').location['x']
    assert '?v=' in driver.find_element(By.CSS_SELECTOR, 'script[src]').get_attribute('src')
    assert '?v=' in driver.find_element(By.CSS_SELECTOR, 'link[rel=stylesheet]').get_attribute('href')
