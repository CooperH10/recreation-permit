#!/usr/bin/env python3

import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.keys import Keys

# =========================
# CONFIGURATION
# =========================

PERMIT_ID = "445857"
TARGET_DATE = "2026-08-02"   # YYYY-MM-DD
GROUP_SIZE = 5
PERMIT_NAME = "High Sierra Trail"

# Path to your pre-logged-in Firefox profile
BASE_PROFILE_PATH = r"/Users/charris4/Library/Application Support/Firefox/Profiles/18mzjavg.default-release"

# =========================
# URL BUILDER
# =========================

def build_url():
    return (
        f"https://www.recreation.gov/permits/{PERMIT_ID}/"
        f"registration/detailed-availability"
        f"?date={TARGET_DATE}&type=overnight-permit"
    )

# =========================
# DRIVER SETUP
# =========================

def start_driver(profile_path):
    options = Options()
    options.profile = profile_path
    # options.add_argument("--headless")
    options.add_argument("--width=800")
    options.add_argument("--height=600")

    # --- Performance preferences ---
    options.set_preference("permissions.default.image", 2)   # disable images
    options.set_preference("gfx.downloadable_fonts.enabled", False)
    options.set_preference("media.autoplay.default", 5)
    options.set_preference("media.autoplay.blocking_policy", 2)
    options.set_preference("dom.animations.enabled", False)
    options.set_preference("layout.css.prefers-reduced-motion", 1)
    options.set_preference("network.http.speculative-parallel-limit", 0)
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    options.set_preference("media.navigator.enabled", False)
    options.set_preference("media.peerconnection.enabled", False)
    options.set_preference("dom.serviceWorkers.enabled", False)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("dom.push.enabled", False)
    options.set_preference("dom.webcomponents.enabled", False)
    options.set_preference("dom.webgpu.enabled", False)
    options.set_preference("beacon.enabled", False)
    options.set_preference("network.dns.disablePrefetch", True)
    options.set_preference("network.dns.disablePrefetchFromHTTPS", True)
    options.set_preference("network.predictor.enabled", False)
    options.set_preference("network.prefetch-next", False)

    # Reduce detection
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)

    driver = webdriver.Firefox(options=options)
    return driver

# =========================
# PAGE INTERACTIONS
# =========================

def wait_for_app(driver):
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "recApp")))

def set_group_size(driver, target=GROUP_SIZE):

    # 1) Open the dropdown if it isn't already open
    trigger = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.ID, "guest-counter"))
    )

    if trigger.get_attribute("aria-expanded") == "false":
        trigger.click()

    # 2) Now wait for the REAL input to appear
    people_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located(
            (By.ID, "guest-counter-number-field-People")
        )
    )

    # 3) Clear + type (this is what React actually listens to)
    people_input.clear()
    people_input.send_keys(str(target))

    # 4) Trigger React change explicitly
    driver.execute_script("""
      arguments[0].dispatchEvent(new Event('input', {bubbles:true}));
      arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
    """, people_input)

    # 5) Close the popup so the grid refreshes
    close_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[@id='guest-counter-popup']//button[.//span[text()='Close']]"
        ))
    )
    close_btn.click()

def set_date(driver, date_str):
    target = datetime.strptime(date_str, "%Y-%m-%d")

    # 1) Click to focus the date picker inputs
    toggle = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "single-date-toggle"))
    )
    toggle.click()

    # 2) Wait for inputs to appear
    month_input = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.date-segment[aria-label='month, ']"))
    )
    day_input = driver.find_element(By.CSS_SELECTOR, "div.date-segment[aria-label='day, ']")
    year_input = driver.find_element(By.CSS_SELECTOR, "div.date-segment[aria-label='year, ']")

    # 3) Clear & type each value (mimics user input)
    for input_elem, value in [(month_input, target.month), (day_input, target.day), (year_input, target.year)]:
        input_elem.click()
        input_elem.send_keys(str(value))

def select_permit_for_date(driver, permit_name):
    row = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((
            By.XPATH,
            f".//div[@role='row'][.//button[normalize-space()='{permit_name}']]"
        ))
    )

    date_buttons = row.find_elements(
        By.XPATH,
        ".//div[contains(@class,'rec-grid-grid-cell')]//button[contains(@class,'rec-availability-date')]"
    )
    if not date_buttons:
        raise RuntimeError("No online reservations available")

    for btn in date_buttons:
        if "No online reservations available" in btn.get_attribute("aria-label"):
            raise RuntimeError("No online reservations available")

    date_button = date_buttons[0]
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior:'instant', block:'center'});", date_button
    )
    try:
        date_button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", date_button)

    WebDriverWait(row, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            ".//div[contains(@class,'rec-grid-grid-cell') and contains(@class,'selected')]"
        ))
    )

def click_book_now(driver):
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//text()[contains(., 'Book Now')]]"))
    ).click()

# =========================
# BOT LOOP
# =========================

def run_single_tab_bot():
    driver = start_driver(BASE_PROFILE_PATH)
    driver.get(build_url())
    wait_for_app(driver)
    set_date(driver, TARGET_DATE)
    set_group_size(driver)

    print("[BOT] Starting availability loop...")
    iteration = 0
    while True:
        iteration += 1
        t0 = time.perf_counter()
        try:
            select_permit_for_date(driver, PERMIT_NAME)
            click_book_now(driver)
            print("[BOT] SUCCESS — reached booking stage!")
            break
        except RuntimeError as e:
            if "No online reservations available" in str(e):
                print("[BOT] No reservations, refreshing...")
                driver.get(driver.current_url)   # reload via navigation, not .refresh()
                wait_for_app(driver)
                set_date(driver, TARGET_DATE)
                set_group_size(driver)
            else:
                print(f"[BOT] ERROR: {e}")
                break
        except Exception as e:
            print(f"[BOT] FAILED: {e}")
            break

        elapsed = time.perf_counter() - t0
        print(f"[BOT] Iteration {iteration} completed in {elapsed:.2f}s")

    # Keep the tab open for manual checkout
    print("[BOT] Leaving browser open for checkout")
    input("Press Enter to exit and close browser...")
    driver.quit()

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    if not os.path.exists(BASE_PROFILE_PATH):
        print(f"ERROR: Base profile path does not exist: {BASE_PROFILE_PATH}")
        exit(1)

    run_single_tab_bot()
