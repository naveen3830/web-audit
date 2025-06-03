import os
import time
import logging
import pyautogui
import pygetwindow as gw
from PIL import ImageGrab
import cv2
import numpy as np
from threading import Thread, Event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("sf_automation.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3
BASE = os.path.abspath(os.path.dirname(__file__))

# Image paths
START_BTN_IMG = os.path.join(BASE, r"images\sf_start_button.png")
URLBAR_IMG = os.path.join(BASE, r"images\sf_urlbar.png")
OK_BUTTON_IMG = os.path.join(BASE, r"images\sf_limit_dialog.png")

# Debug directory setup
debug_dir = os.path.join(BASE, "debug")
os.makedirs(debug_dir, exist_ok=True)

# Global flag to indicate if crawl is complete
crawl_complete = False


def take_debug_screenshot(name):
    """Take a screenshot for debugging purposes"""
    filename = os.path.join(debug_dir, f"{name}_{int(time.time())}.png")
    pyautogui.screenshot(filename)
    logger.info(f"Debug screenshot saved: {filename}")
    return filename


def find_green_crawl_indicator():
    """Look for the green 'Crawl 100%' indicator using better color detection"""
    try:
        screenshot = ImageGrab.grab()
        screenshot_np = np.array(screenshot)

        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2HSV)

        # Green color range in HSV
        lower_green = np.array([40, 100, 100])
        upper_green = np.array([80, 255, 255])

        # Create mask and find contours
        mask = cv2.inRange(hsv, lower_green, upper_green)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Save the mask for debugging
        cv2.imwrite(os.path.join(debug_dir, f"green_mask_{int(time.time())}.png"), mask)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            # Looking for green areas that might be progress indicators
            if w > 50 and 10 < h < 30:
                logger.info(
                    f"Found possible green indicator at x={x}, y={y}, width={w}, height={h}"
                )
                # Draw rectangle on debug image
                debug_img = screenshot_np.copy()
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.imwrite(
                    os.path.join(debug_dir, f"green_indicator_{int(time.time())}.png"),
                    cv2.cvtColor(debug_img, cv2.COLOR_RGB2BGR),
                )
                return (x, y, w, h)
    except Exception as e:
        logger.error(f"Error in find_green_crawl_indicator: {e}")

    return None


def monitor_for_crawl_completion(stop_event):
    """Background thread to monitor for crawl completion"""
    global crawl_complete

    check_interval = 3  # Check every 3 seconds
    logger.info("Started monitoring for crawl completion...")

    while not stop_event.is_set():
        if find_green_crawl_indicator():
            logger.info("✅ Crawl appears to be complete!")
            take_debug_screenshot("crawl_complete_detected")
            crawl_complete = True
            return

        time.sleep(check_interval)


def find_window(possible_titles):
    """Find window by multiple possible titles"""
    for title in possible_titles:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            return wins[0]
    return None


def is_dialog_present(dialog_titles):
    """Check if any dialog with the given titles is present"""
    for title in dialog_titles:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            return wins[0]
    return None


def click_ok_button():
    """Find and click the OK button on the limit dialog using multiple methods"""
    try:
        # Method 1: Try to find the dialog window first
        dialog_titles = ["Crawl Limit Reached", "Limit", "SEO Spider"]
        dialog_win = is_dialog_present(dialog_titles)

        if dialog_win:
            logger.info(f"Found dialog window: {dialog_win.title}")
            take_debug_screenshot("found_dialog_window")

            # Try to focus the dialog
            dialog_win.activate()
            time.sleep(0.5)

            # Method 2: Try image recognition for the OK button
            try:
                # Take a screenshot of just the dialog area for better detection
                dialog_screenshot = pyautogui.screenshot(
                    region=(
                        dialog_win.left,
                        dialog_win.top,
                        dialog_win.width,
                        dialog_win.height,
                    )
                )

                # Save this for debugging
                dialog_screenshot.save(
                    os.path.join(debug_dir, f"dialog_window_{int(time.time())}.png")
                )

                # Now try to find the OK button in the full screen
                ok_button = pyautogui.locateOnScreen(OK_BUTTON_IMG, confidence=0.6)
                if ok_button:
                    logger.info("Found OK button using image recognition!")
                    ok_center = pyautogui.center(ok_button)
                    pyautogui.click(ok_center)
                    time.sleep(0.5)
                    return True
            except Exception as e:
                logger.error(f"Error finding OK button via image: {e}")

            # Method 3: Try clicking at common locations for the OK button

            # Bottom right (common for OK buttons)
            ok_x = dialog_win.left + dialog_win.width - 70
            ok_y = dialog_win.top + dialog_win.height - 40
            logger.info(f"Trying to click OK button at position x={ok_x}, y={ok_y}")
            pyautogui.click(ok_x, ok_y)
            time.sleep(0.5)

            # Check if dialog is still present
            if not is_dialog_present(dialog_titles):
                logger.info("Dialog closed after clicking!")
                return True

            # Method 4: Press Enter key as a last resort
            logger.info("Trying Enter key to dismiss dialog")
            pyautogui.press("enter")
            time.sleep(0.5)

            # Final check
            if not is_dialog_present(dialog_titles):
                logger.info("Dialog closed after pressing Enter!")
                return True

            logger.warning("All attempts to close dialog failed")
            return False

    except Exception as e:
        logger.error(f"Error in click_ok_button: {e}")

    # Try Enter key even if we didn't find a dialog (it might be there but not detected)
    logger.info("Trying Enter key as a final attempt")
    pyautogui.press("enter")
    time.sleep(0.5)
    return False


def find_and_click_export_button():
    """Find and click the Export button"""
    try:
        # Method 1: Try to find export button by image recognition
        export_img = os.path.join(BASE, r"images\sf_export_button.png")
        export_btn = pyautogui.locateOnScreen(export_img, confidence=0.7)
        if export_btn:
            logger.info("Found Export button using image recognition!")
            export_center = pyautogui.center(export_btn)
            pyautogui.click(export_center)
            take_debug_screenshot("after_export_click")
            return True
    except Exception as e:
        logger.error(f"Error finding Export button via image: {e}")

    # Method 2: Try to find using typical locations
    try:
        # Try to find the Screaming Frog window again
        sf_win = find_window(
            ["Screaming Frog SEO Spider", "Screaming Frog", "SEO Spider"]
        )
        if sf_win:
            # Export is often in the toolbar near the top
            export_x = sf_win.left + 60  # Approximate position for Export button
            export_y = (
                sf_win.top + 70
            )  # Adjusted to match the Export button in your image
            pyautogui.click(export_x, export_y)
            logger.info(
                f"Clicked estimated Export button position at {export_x}, {export_y}"
            )
            take_debug_screenshot("after_estimated_export_click")
            return True
    except Exception as e:
        logger.error(f"Error clicking estimated Export position: {e}")

    # Method 3: Try keyboard shortcut (Ctrl+E is common for Export)
    try:
        pyautogui.hotkey("ctrl", "e")
        logger.info("Used Ctrl+E shortcut for Export")
        take_debug_screenshot("after_export_shortcut")
        return True
    except Exception as e:
        logger.error(f"Error using Export shortcut: {e}")

    return False


def handle_save_dialog(filename="internal_all.csv", directory=None):
    """Handle the Save dialog by entering filename and clicking Save"""
    try:
        # Wait for the save dialog to appear
        time.sleep(2)
        take_debug_screenshot("save_dialog_expected")

        # Look for dialog window
        save_dialog = find_window(["Save", "Save As", "Save Location"])

        if save_dialog:
            logger.info(f"Found save dialog: {save_dialog.title}")
            save_dialog.activate()
            time.sleep(0.5)

            # Enter filename (first field)
            pyautogui.press("tab")  # Ensure focus
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")  # Select all text
            time.sleep(0.5)
            pyautogui.write(filename, interval=0.05)
            logger.info(f"Entered filename: {filename}")

            # If directory is specified, navigate to it
            if directory:
                # Tab to the directory field
                pyautogui.press("tab")
                time.sleep(0.5)
                pyautogui.press("tab")  # May need another tab depending on dialog
                time.sleep(0.5)
                pyautogui.hotkey("ctrl", "a")  # Select all text
                time.sleep(0.5)
                pyautogui.write(directory, interval=0.05)
                logger.info(f"Entered directory: {directory}")

            # Look for the Save button using image recognition
            save_img = os.path.join(BASE, r"images\sf_save_button.png")
            try:
                save_btn = pyautogui.locateOnScreen(save_img, confidence=0.7)
                if save_btn:
                    logger.info("Found Save button using image recognition!")
                    save_center = pyautogui.center(save_btn)
                    pyautogui.click(save_center)
                    take_debug_screenshot("after_save_click")
                    return True
            except Exception as e:
                logger.error(f"Error finding Save button via image: {e}")

            # Alternative: Try to find the green Save button
            try:
                # Take a screenshot
                screenshot = ImageGrab.grab()
                screenshot_np = np.array(screenshot)

                # Convert to HSV for green detection
                hsv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2HSV)

                # Green color range in HSV
                lower_green = np.array([40, 100, 100])
                upper_green = np.array([80, 255, 255])

                # Create mask and find contours
                mask = cv2.inRange(hsv, lower_green, upper_green)
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    # Looking for green buttons
                    if 50 < w < 150 and 20 < h < 50:
                        logger.info(
                            f"Found possible green Save button at x={x}, y={y}, width={w}, height={h}"
                        )
                        # Click the center of the button
                        center_x = x + (w // 2)
                        center_y = y + (h // 2)
                        pyautogui.click(center_x, center_y)
                        logger.info(
                            f"Clicked green button at x={center_x}, y={center_y}"
                        )
                        take_debug_screenshot("after_green_save_click")
                        return True
            except Exception as e:
                logger.error(f"Error finding green Save button: {e}")

            # Final fallback: Try tab navigation to Save button
            try:
                # Assuming we're in the filename field, tab to save button and press Enter
                for _ in range(5):  # Tab enough times to reach Save button
                    pyautogui.press("tab")
                    time.sleep(0.3)

                pyautogui.press("enter")
                logger.info("Used tab navigation and Enter to save")
                take_debug_screenshot("after_tab_save")
                return True
            except Exception as e:
                logger.error(f"Error using tab navigation to save: {e}")

    except Exception as e:
        logger.error(f"Error handling save dialog: {e}")

    return False


def is_application_ready(window):
    """Verify that the application is fully loaded and ready for input"""
    if not window:
        return False

    try:
        # Take a screenshot of the window
        screenshot = pyautogui.screenshot(
            region=(window.left, window.top, window.width, window.height)
        )

        # Save this for debugging
        screenshot.save(
            os.path.join(debug_dir, f"app_readiness_check_{int(time.time())}.png")
        )

        # Check for URL bar presence using image recognition
        try:
            url_loc = pyautogui.locateOnScreen(URLBAR_IMG, confidence=0.7)
            if url_loc:
                logger.info("URL bar found - application appears ready")
                return True
        except Exception:
            pass

        # Alternative: Check if the window size is reasonable (not minimized)
        if window.width > 100 and window.height > 100:
            # Wait a bit more to ensure UI elements are loaded
            time.sleep(3)
            logger.info("Window has reasonable size - assuming application is ready")
            return True

    except Exception as e:
        logger.error(f"Error checking if application is ready: {e}")

    return False


def wait_for_url_bar(sf_window, max_attempts=10):
    """Wait and verify that the URL bar is present and ready for input"""
    for attempt in range(max_attempts):
        try:
            # Method 1: Image recognition
            url_loc = pyautogui.locateOnScreen(URLBAR_IMG, confidence=0.7)
            if url_loc:
                logger.info(f"URL bar found on attempt {attempt + 1}")
                take_debug_screenshot("url_bar_found")
                return True

            # Take screenshot for debugging
            if attempt % 2 == 0:  # Every other attempt
                take_debug_screenshot(f"url_bar_search_attempt_{attempt}")

            # Make sure window is active
            sf_window.activate()
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error during URL bar detection attempt {attempt + 1}: {e}")

        time.sleep(2)  # Wait before next attempt

    logger.warning("URL bar could not be found after multiple attempts")
    return False


def enter_url_safely(sf_window, url):
    """Safely enter URL ensuring the URL bar is ready"""
    try:
        # First try Alt+D to focus URL bar
        sf_window.activate()
        time.sleep(1)
        pyautogui.hotkey("alt", "d")
        time.sleep(1)

        # Clear any existing text
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.5)

        # Type the URL slowly
        pyautogui.write(url, interval=0.05)
        take_debug_screenshot("after_url_entry")
        logger.info(f"Entered URL: {url}")
        return True
    except Exception as e:
        logger.error(f"Error entering URL: {e}")
        return False


def wait_for_complete_crawl_then_export():
    """Wait for the crawl to fully complete (100%) before attempting to export"""
    logger.info("Waiting for crawl to fully complete before exporting...")

    start_time = time.time()
    max_wait_time = 600  # 10 minutes max wait
    check_interval = 5  # Check every 5 seconds

    while time.time() - start_time < max_wait_time:
        try:
            # Take a debug screenshot periodically
            if int(time.time() - start_time) % 30 == 0:
                take_debug_screenshot(f"waiting_for_complete_crawl_{int(time.time())}")

            # Find the Screaming Frog window
            sf_win = find_window(
                ["Screaming Frog SEO Spider", "Screaming Frog", "SEO Spider"]
            )
            if not sf_win:
                logger.warning("Cannot find Screaming Frog window")
                time.sleep(check_interval)
                continue

            # Take a screenshot of the bottom status bar area
            # This is where the "Completed X of Y" text appears
            bottom_y = sf_win.bottom - 35  # Approximate Y position of status bar
            left_x = sf_win.left + sf_win.width // 2  # Middle of the window
            status_width = (
                sf_win.width // 3
            )  # Capture about 1/3 of the width where status text is

            status_screenshot = ImageGrab.grab(
                bbox=(left_x, bottom_y - 20, left_x + status_width, bottom_y + 20)
            )

            # Save for debugging
            status_path = os.path.join(debug_dir, f"status_bar_{int(time.time())}.png")
            status_screenshot.save(status_path)

            # Convert to OpenCV format for processing
            status_np = np.array(status_screenshot)

            # Check if the status bar shows 100% completion
            # We can use color detection to look for the green progress indicator

            # Method 1: Check if "Remaining" text is gone or "0 Remaining"
            # This would require OCR, but without adding dependencies, we'll use a color-based approach

            # Method 2: Look at progress bar at the top of the window
            top_bar_y = sf_win.top + 60  # Approximate Y position of the progress bar
            progress_screenshot = ImageGrab.grab(
                bbox=(sf_win.left, top_bar_y - 10, sf_win.right, top_bar_y + 10)
            )

            progress_path = os.path.join(
                debug_dir, f"progress_bar_{int(time.time())}.png"
            )
            progress_screenshot.save(progress_path)

            progress_np = np.array(progress_screenshot)
            hsv = cv2.cvtColor(progress_np, cv2.COLOR_RGB2HSV)

            # Look for green pixels (the progress bar)
            lower_green = np.array([40, 100, 100])
            upper_green = np.array([80, 255, 255])
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Calculate what percentage of the width is filled with green
            green_width = np.sum(mask > 0) / mask.size
            logger.info(f"Progress bar fill: {green_width:.2%}")

            # If progress is at least 99%, consider it done
            if green_width > 0.99:
                logger.info(
                    "✅ Crawl appears to be 100% complete based on progress bar!"
                )

                # Take a full screenshot to verify
                take_debug_screenshot("crawl_detected_complete")

                # Extra check: Wait a bit to ensure any animations or status updates finish
                time.sleep(5)

                # Now proceed with export
                return True

            # Also check the Status panel
            # Look for "Completed X of Y (100%)" text at the bottom
            bottom_status = ImageGrab.grab(
                bbox=(
                    sf_win.right - 300,
                    sf_win.bottom - 30,
                    sf_win.right,
                    sf_win.bottom,
                )
            )

            bottom_status_path = os.path.join(
                debug_dir, f"bottom_status_{int(time.time())}.png"
            )
            bottom_status.save(bottom_status_path)

            logger.info(
                "Waiting for crawl to finish... Check debug images if available."
            )

        except Exception as e:
            logger.error(f"Error checking crawl completion: {e}")

        # Check for and dismiss any dialogs that might appear during waiting
        try:
            dialog_titles = ["Crawl Limit Reached", "Limit", "SEO Spider"]
            dialog_win = is_dialog_present(dialog_titles)
            if dialog_win:
                logger.info("Dialog detected during wait!")
                if click_ok_button():
                    logger.info("Successfully handled dialog during wait")
        except Exception:
            pass

        time.sleep(check_interval)

    logger.warning("Timed out waiting for crawl to fully complete")
    return False


def export_after_completion():
    """Export the crawl results after ensuring the crawl is fully complete"""
    logger.info("Starting export process...")

    # First, make sure the crawl is fully complete
    if not wait_for_complete_crawl_then_export():
        logger.warning("Cannot export because crawl did not fully complete")
        return False

    # Now proceed with the export
    logger.info("Crawl is complete, proceeding with export...")

    # Get the Screaming Frog window
    sf_win = find_window(["Screaming Frog SEO Spider", "Screaming Frog", "SEO Spider"])
    if not sf_win:
        logger.error("Cannot find Screaming Frog window for export")
        return False

    # Ensure window is active
    sf_win.activate()
    time.sleep(1)

    # Method 1: Use keyboard shortcuts to navigate to Bulk Export > Internal
    try:
        logger.info("Trying keyboard shortcuts for Bulk Export > Internal")

        # First press Alt to activate the menu
        pyautogui.press("alt")
        time.sleep(1)

        # Focus on the "Bulk Export" menu (5th item in the menu bar)
        for _ in range(
            4
        ):  # Skip past File, View, Mode, Configuration to reach Bulk Export
            pyautogui.press("right")
            time.sleep(0.5)

        # Open the Bulk Export menu
        pyautogui.press("enter")
        time.sleep(1)
        take_debug_screenshot("after_bulk_export_menu")

        # Select "Internal" from the menu (usually the first item)
        pyautogui.press("i")  # First letter navigation or
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(1)
        take_debug_screenshot("after_internal_selection")

        # Now the save dialog should appear
        time.sleep(2)

        # Handle the save dialog
        save_dialog = find_window(["Save", "Save As", "Export", "Export As"])
        if save_dialog:
            logger.info("Found save dialog after export")

            # Define save location and filename
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            filename = f"screaming_frog_export_{int(time.time())}.csv"

            if handle_save_dialog(filename=filename, directory=downloads_dir):
                logger.info(f"✅ Successfully saved export to {filename}!")
                return True
    except Exception as e:
        logger.error(f"Error in keyboard export method: {e}")

    # Method 2: Try clicking the Bulk Export in menu bar directly
    try:
        logger.info("Trying direct click on Bulk Export menu")

        # Click on "Bulk Export" in the menu bar
        bulk_export_x = (
            sf_win.left + 242
        )  # Approximate X position based on your screenshot
        bulk_export_y = sf_win.top + 30  # Approximate Y position of menu bar

        pyautogui.click(bulk_export_x, bulk_export_y)
        time.sleep(1)
        take_debug_screenshot("after_bulk_export_click")

        # Now click on "Internal" in the dropdown menu
        internal_x = bulk_export_x
        internal_y = bulk_export_y + 40  # First item in dropdown

        pyautogui.click(internal_x, internal_y)
        time.sleep(1)
        take_debug_screenshot("after_internal_click")

        # Handle the save dialog
        time.sleep(2)
        save_dialog = find_window(["Save", "Save As", "Export", "Export As"])
        if save_dialog:
            logger.info("Found save dialog after export")

            # Define save location and filename
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            filename = f"screaming_frog_export_{int(time.time())}.csv"

            if handle_save_dialog(filename=filename, directory=downloads_dir):
                logger.info(f"✅ Successfully saved export to {filename}!")
                return True
    except Exception as e:
        logger.error(f"Error in direct click export method: {e}")

    # Method 3: Try using bottom Export button
    try:
        logger.info("Trying export via bottom Export button")

        # Click on the Export button at the bottom-left of the window
        bottom_export_x = sf_win.left + 45  # Approximate X position based on screenshot
        bottom_export_y = sf_win.bottom - 35  # Approximate Y position of bottom toolbar

        pyautogui.click(bottom_export_x, bottom_export_y)
        time.sleep(1)
        take_debug_screenshot("after_bottom_export_click")

        # Handle the save dialog or subsequent menus
        time.sleep(2)

        # Check for save dialog
        save_dialog = find_window(["Save", "Save As", "Export", "Export As"])
        if save_dialog:
            logger.info("Found save dialog after export")

            # Define save location and filename
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            filename = f"screaming_frog_export_{int(time.time())}.csv"

            if handle_save_dialog(filename=filename, directory=downloads_dir):
                logger.info(f"✅ Successfully saved export to {filename}!")
                return True
        else:
            # Maybe we need to navigate through menus first
            # Try clicking in the approximate location where a context menu might appear
            menu_x = bottom_export_x + 50
            menu_y = bottom_export_y - 50

            pyautogui.click(menu_x, menu_y)
            time.sleep(1)
            take_debug_screenshot("after_export_menu_click")

            # Check for save dialog again
            time.sleep(2)
            save_dialog = find_window(["Save", "Save As", "Export", "Export As"])
            if save_dialog:
                # Handle the save dialog
                downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                filename = f"screaming_frog_export_{int(time.time())}.csv"

                if handle_save_dialog(filename=filename, directory=downloads_dir):
                    logger.info(f"✅ Successfully saved export to {filename}!")
                    return True
    except Exception as e:
        logger.error(f"Error in bottom export button method: {e}")

    logger.warning("All export methods failed")
    return False


def main():
    global crawl_complete

    logger.info("=== Starting Screaming Frog Automation ===")

    # 1. Check if Screaming Frog is already running
    possible_titles = ["Screaming Frog SEO Spider", "Screaming Frog", "SEO Spider"]
    sf_win = find_window(possible_titles)

    if sf_win:
        logger.info(f"Screaming Frog is already running: {sf_win.title}")
    else:
        # Start Screaming Frog
        sf_shortcut = (
            r"C:\ProgramData\Microsoft\Windows\Start Menu"
            r"\Programs\Screaming Frog SEO Spider.lnk"
        )

        try:
            logger.info("Starting Screaming Frog...")
            os.startfile(sf_shortcut)

            # Wait for Screaming Frog to start (with extended timeout)
            start_time = time.time()
            max_wait = 60  # Extended to 60 seconds for slow systems

            while time.time() - start_time < max_wait:
                sf_win = find_window(possible_titles)
                if sf_win:
                    logger.info(f"Found window with title: {sf_win.title}")
                    # Wait additional time for application to fully initialize
                    time.sleep(5)
                    break
                time.sleep(2)
        except Exception as e:
            logger.error(f"Failed to start Screaming Frog: {e}")
            take_debug_screenshot("start_error")
            return False

    if not sf_win:
        logger.error(
            "❌ Couldn't find the Screaming Frog window—make sure it's installed and running."
        )
        take_debug_screenshot("no_window_found")
        return False

    # 2. Focus and maximize window
    try:
        sf_win.activate()
        time.sleep(2)  # Increased wait time
        sf_win.maximize()
        time.sleep(3)  # Longer wait after maximize
        logger.info("Activated and maximized Screaming Frog window.")
        take_debug_screenshot("after_activation")
    except Exception as e:
        logger.error(f"Error activating window: {e}")
        take_debug_screenshot("activation_error")

    # 3. Verify application is ready for input
    logger.info("Verifying application is ready...")
    ready_attempts = 0
    while ready_attempts < 5:  # Try up to 5 times
        if is_application_ready(sf_win):
            logger.info("✅ Application is ready for input!")
            break

        logger.info(
            f"Application not ready yet, waiting... (attempt {ready_attempts + 1}/5)"
        )
        time.sleep(3)
        ready_attempts += 1

        # Refresh window handle
        sf_win = find_window(possible_titles)
        if not sf_win:
            logger.error(
                "❌ Lost window handle while waiting for application to be ready"
            )
            take_debug_screenshot("lost_window")
            return False

    # 4. Wait specifically for URL bar to be ready
    logger.info("Waiting for URL bar to be available...")
    if not wait_for_url_bar(sf_win):
        logger.warning("⚠️ Proceeding without visual confirmation of URL bar")

    # 5. Enter URL with improved safety
    url_to_crawl = "https://www.leadwalnut.com/"
    if not enter_url_safely(sf_win, url_to_crawl):
        logger.error("❌ Failed to enter URL safely")
        take_debug_screenshot("url_entry_failed")
        return False

    # 6. Click Start button using multiple methods
    logger.info("Looking for Start button...")
    start_clicked = False

    # Method 1: Image recognition
    try:
        btn = pyautogui.locateOnScreen(START_BTN_IMG, confidence=0.7)
        if btn:
            pyautogui.click(pyautogui.center(btn))
            logger.info("Clicked Start button using image recognition.")
            start_clicked = True
    except Exception as e:
        logger.error(f"Error finding start button via image: {e}")

    if not start_clicked:
        # Method 2: Press Enter
        try:
            pyautogui.press("enter")
            logger.info("Pressed Enter to start crawl.")
            start_clicked = True
        except Exception as e:
            logger.error(f"Error pressing Enter: {e}")

    if not start_clicked:
        # Method 3: Try common position
        try:
            sf_win = find_window(possible_titles)
            if sf_win:
                right_side_x = sf_win.left + sf_win.width - 100
                top_y = sf_win.top + 42
                pyautogui.click(right_side_x, top_y)
                logger.info("Clicked estimated Start button position.")
                start_clicked = True
        except Exception as e:
            logger.error(f"Error clicking estimated position: {e}")

    take_debug_screenshot("after_start_click")

    # 7. Wait for crawl completion in a separate thread (non-blocking)
    stop_monitoring = Event()

    # Start the monitoring thread
    monitor_thread = Thread(
        target=monitor_for_crawl_completion, args=(stop_monitoring,)
    )
    monitor_thread.daemon = True
    monitor_thread.start()

    # Wait for the crawl to complete, checking at intervals
    logger.info("Waiting for crawl to complete...")
    start_time = time.time()
    max_wait_time = 300  # 5 minutes max wait
    interval_screenshot = 30  # Take screenshot every 30 seconds

    while time.time() - start_time < max_wait_time:
        if crawl_complete:
            logger.info("Crawl completion detected!")
            break

        # Take periodic screenshots
        elapsed = int(time.time() - start_time)
        if elapsed % interval_screenshot < 1:
            take_debug_screenshot(f"waiting_for_crawl_{elapsed // 30}")

        # Also check for dialog boxes periodically
        dialog_titles = ["Crawl Limit Reached", "Limit", "SEO Spider"]
        dialog_win = is_dialog_present(dialog_titles)
        if dialog_win:
            logger.info("Dialog detected during crawl!")
            if click_ok_button():
                logger.info("Successfully handled dialog during crawl")

        # Wait a bit before next check
        time.sleep(2)

    # Stop the monitoring thread
    stop_monitoring.set()

    if not crawl_complete:
        logger.warning("⚠️ Crawl did not complete within timeout period.")
        take_debug_screenshot("crawl_timeout")
    else:
        logger.info("Moving on to check for limit dialog...")

    # 8. Wait for and handle the "Limit Reached" dialog
    logger.info("Checking for the Crawl Limit Reached dialog...")
    start_time = time.time()
    max_wait_time = 60  # 1 minute max wait time
    limit_dialog_handled = False
    check_interval = 2  # Check every 2 seconds

    while time.time() - start_time < max_wait_time:
        dialog_titles = ["Crawl Limit Reached", "Limit", "SEO Spider"]
        dialog_win = is_dialog_present(dialog_titles)

        if dialog_win:
            logger.info(f"Found dialog window: {dialog_win.title}")
            if click_ok_button():
                logger.info("✅ Successfully handled the limit dialog!")
                take_debug_screenshot("after_handling_dialog")
                limit_dialog_handled = True
                break

        # If crawl is complete and no dialog after some time, we can exit
        if crawl_complete and (time.time() - start_time > 15):
            logger.info("Crawl is complete and no dialog appeared after 15 seconds.")
            break

        # Wait before next check
        time.sleep(check_interval)

    if not limit_dialog_handled and not crawl_complete:
        logger.warning("⚠️ Limit dialog not detected within timeout period.")
        take_debug_screenshot("dialog_timeout")

    # 9. Export the results
    if crawl_complete:
        logger.info("Attempting to export crawl results...")
        export_success = export_after_completion()

        if export_success:
            logger.info("✅ Export successful!")
        else:
            logger.warning("⚠️ Export failed or could not be completed")

        # Try clicking export
        for attempt in range(3):  # Try up to 3 times
            logger.info(f"Export attempt {attempt + 1}...")
            if find_and_click_export_button():
                time.sleep(2)  # Wait for export menu/dialog
                take_debug_screenshot(f"after_export_attempt_{attempt + 1}")
                try:
                    internal_option_x = pyautogui.position().x  # Use current X position
                    internal_option_y = (
                        pyautogui.position().y + 100
                    )  # Offset down to find Internal option
                    pyautogui.click(internal_option_x, internal_option_y)
                    logger.info("Clicked 'Internal' option from export menu")
                    time.sleep(1)
                    take_debug_screenshot("after_internal_click")

                    # Check if save dialog appeared
                    save_dialog = find_window(["Save", "Save As", "Save Location"])
                    if save_dialog:
                        # Define save location and filename
                        downloads_dir = os.path.join(
                            os.path.expanduser("~"), "Downloads"
                        )

                        # Handle the save dialog
                        if handle_save_dialog(
                            filename="internal_all.csv", directory=downloads_dir
                        ):
                            logger.info("✅ Successfully saved export file!")
                            export_success = True
                            break
                except Exception as e:
                    logger.error(f"Error during export process: {e}")

            time.sleep(2)  # Wait before next attempt

        if not export_success:
            logger.warning("⚠️ Failed to export crawl results after multiple attempts")
    else:
        logger.warning("⚠️ Cannot export results because crawl did not complete")

    # 10. Final screenshot and output
    time.sleep(2)  # Give a moment for any UI changes
    final_screenshot = take_debug_screenshot("final_state")
    logger.info(f"✅ Done—final screenshot saved as {final_screenshot}")

    # Also save with standard filename
    pyautogui.screenshot("sf_after_crawl.png")
    logger.info("✅ Standard screenshot also saved as sf_after_crawl.png")

    return True


if __name__ == "__main__":
    main()
