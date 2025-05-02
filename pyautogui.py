import os
import time
import pyautogui
import pygetwindow as gw
from PIL import ImageGrab, Image
import cv2
import numpy as np

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5
BASE = os.path.abspath(os.path.dirname(__file__))

START_BTN_IMG = os.path.join(BASE, 'sf_start_button.png')
URLBAR_IMG = os.path.join(BASE, 'sf_urlbar.png')
OK_BUTTON_IMG = os.path.join(BASE, 'sf_limit_dialog')  

debug_dir = os.path.join(BASE, 'debug')
os.makedirs(debug_dir, exist_ok=True)

def take_debug_screenshot(name):
    """Take a screenshot for debugging purposes"""
    filename = os.path.join(debug_dir, f"{name}_{int(time.time())}.png")
    pyautogui.screenshot(filename)
    print(f"Debug screenshot saved: {filename}")
    return filename

def find_green_crawl_indicator():
    """Look for the green 'Crawl 100%' indicator"""
    screenshot = ImageGrab.grab()
    screenshot_np = np.array(screenshot)
    
    hsv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2HSV)
    
    lower_green = np.array([40, 100, 100])
    upper_green = np.array([80, 255, 255])
    
    mask = cv2.inRange(hsv, lower_green, upper_green)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > 100 and h > 10 and h < 30:
            print(f"Found possible green indicator at x={x}, y={y}, width={w}, height={h}")
            return (x, y, w, h)
    
    return None

def is_crawl_complete():
    """Check if crawl has reached 100%"""
    green_indicator = find_green_crawl_indicator()
    if green_indicator:
        print("Found green crawl indicator - crawl may be complete!")
        return True
    return False

def click_ok_button():
    """Find and click the OK button on the limit dialog"""
    try:
        ok_button = pyautogui.locateOnScreen(OK_BUTTON_IMG, confidence=0.6)
        if ok_button:
            print("Found OK button using image recognition!")
            take_debug_screenshot("found_ok_button")
            ok_center = pyautogui.center(ok_button)
            pyautogui.click(ok_center)
            return True
    except Exception as e:
        print(f"Error finding OK button via image: {e}")
    
    try:
        limit_dialog = gw.getWindowsWithTitle("Crawl Limit Reached")
        if not limit_dialog:
            limit_dialog = gw.getWindowsWithTitle("Limit")
        
        if limit_dialog:

            limit_dialog[0].activate()
            print("Found and activated limit dialog window!")
            take_debug_screenshot("found_limit_dialog_window")
            
            screenshot = ImageGrab.grab()
            screenshot_np = np.array(screenshot)
            
            hsv = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2HSV)
            lower_green = np.array([40, 100, 100])
            upper_green = np.array([80, 255, 255])
            
            # Create mask for green color
            mask = cv2.inRange(hsv, lower_green, upper_green)
            
            # Find contours in the mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for rectangular green areas that might be buttons
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                # If it's roughly the right shape for a button
                if 30 < w < 100 and 20 < h < 50:
                    # Click the center of the button
                    center_x = x + (w // 2)
                    center_y = y + (h // 2)
                    pyautogui.click(center_x, center_y)
                    print(f"Clicked green button at x={center_x}, y={center_y}")
                    return True
            
            # If no green button found, try bottom right (common place for OK)
            win = limit_dialog[0]
            ok_x = win.left + win.width - 50
            ok_y = win.top + win.height - 30
            pyautogui.click(ok_x, ok_y)
            print(f"Clicked likely OK button position at x={ok_x}, y={ok_y}")
            return True
    except Exception as e:
        print(f"Error handling limit dialog window: {e}")
    
    try:
        pyautogui.press('enter')
        print("Pressed Enter key to confirm dialog")
        return True
    except Exception as e:
        print(f"Error pressing Enter: {e}")
    
    return False

sf_shortcut = (
    r"C:\ProgramData\Microsoft\Windows\Start Menu"
    r"\Programs\Screaming Frog SEO Spider.lnk"
)
os.startfile(sf_shortcut)
print("Starting Screaming Frog...")
time.sleep(10) 

print("Looking for Screaming Frog window...")
possible_titles = ['Screaming Frog', 'Screaming Frog SEO Spider', 'SEO Spider']
sf_win = None

for title in possible_titles:
    wins = gw.getWindowsWithTitle(title)
    if wins:
        sf_win = wins[0]
        print(f"Found window with title: {title}")
        break

if not sf_win:
    print("❌ Couldn't find the Screaming Frog window—make sure it's installed and running.")
    take_debug_screenshot("no_window_found")
    exit(1)

sf_win.activate()
sf_win.maximize()
time.sleep(1)
print("Activated Screaming Frog window.")
take_debug_screenshot("after_activation")

print("Looking for URL bar...")
url_loc = None

try:
    url_loc = pyautogui.locateOnScreen(URLBAR_IMG, confidence=0.7)
except Exception as e:
    print(f"Error during URL bar image recognition: {e}")

if url_loc:
    pyautogui.click(pyautogui.center(url_loc))
    print("Clicked URL bar using image recognition.")
else:
    print("⚠️ URL bar image not found—trying alternative methods")
    
    try:
        win_center_x = sf_win.left + (sf_win.width // 2)
        url_bar_y = sf_win.top + 42
        pyautogui.click(win_center_x, url_bar_y)
        print("Clicked approximate URL bar position.")
    except Exception as e:
        print(f"Error clicking approximate position: {e}")
        
        try:
            pyautogui.hotkey('alt', 'd')
            print("Used Alt+D to focus URL bar.")
        except Exception as e:
            print(f"Error using keyboard shortcut: {e}")

time.sleep(1)
take_debug_screenshot("after_url_bar_click")

pyautogui.hotkey('ctrl', 'a')
time.sleep(0.5)
pyautogui.write('https://www.leadwalnut.com/', interval=0.05)
print("Entered URL.")

print("Looking for Start button...")
start_button_found = False

try:
    btn = pyautogui.locateOnScreen(START_BTN_IMG, confidence=0.7)
    if btn:
        pyautogui.click(pyautogui.center(btn))
        print("Clicked Start button using image recognition.")
        start_button_found = True
except Exception as e:
    print(f"Error finding start button via image: {e}")

if not start_button_found:
    try:
        pyautogui.press('enter')
        print("Pressed Enter to start crawl.")
        start_button_found = True
    except Exception as e:
        print(f"Error pressing Enter: {e}")
        
if not start_button_found:
    try:
        right_side_x = sf_win.left + sf_win.width - 100 
        top_y = sf_win.top + 42
        pyautogui.click(right_side_x, top_y)
        print("Clicked estimated Start button position.")
        start_button_found = True
    except Exception as e:
        print(f"Error clicking estimated position: {e}")

take_debug_screenshot("after_start_click")

print("Waiting for crawl to complete (look for green 'Crawl 100%' indicator)...")
start_time = time.time()
max_wait_time = 300  # 5 minutes max wait time
crawl_complete = False
check_interval = 5  

while time.time() - start_time < max_wait_time:
    # Take periodic screenshots to track progress
    if (time.time() - start_time) % 30 < 1:  # Every ~30 seconds
        take_debug_screenshot(f"waiting_for_crawl_{int((time.time() - start_time) // 30)}")

    if is_crawl_complete():
        print("✅ Crawl appears to be complete!")
        take_debug_screenshot("crawl_complete")
        crawl_complete = True
        break
    
    time.sleep(check_interval)
    elapsed = int(time.time() - start_time)
    print(f"Still waiting for crawl to complete... ({elapsed} seconds elapsed)")

if not crawl_complete:
    print("⚠️ Crawl did not complete within timeout period.")
    take_debug_screenshot("crawl_timeout")
else:
    print("Moving on to check for limit dialog...")
    
# ── 6. Wait for and handle the "Limit Reached" dialog ─────────────
print("Waiting for the Crawl Limit Reached dialog...")
start_time = time.time()
max_wait_time = 60  # 1 minute max wait time
limit_dialog_handled = False
check_interval = 2  # Check every 2 seconds

# Take a screenshot before waiting for dialog
take_debug_screenshot("before_waiting_for_dialog")

while time.time() - start_time < max_wait_time:
    # Check if the limit dialog is present and attempt to click OK
    if click_ok_button():
        print("✅ Successfully handled the limit dialog!")
        take_debug_screenshot("after_handling_dialog")
        limit_dialog_handled = True
        break
    
    # Wait before next check
    time.sleep(check_interval)
    elapsed = int(time.time() - start_time)
    print(f"Still waiting for limit dialog... ({elapsed} seconds elapsed)")

if not limit_dialog_handled:
    print("⚠️ Limit dialog not detected within timeout period.")
    take_debug_screenshot("dialog_timeout")

# ── 7. Final screenshot ─────────────────────────────────────────
time.sleep(2)  # Give a moment for any UI changes
final_screenshot = take_debug_screenshot("final_state")
print(f"✅ Done—final screenshot saved as {final_screenshot}")
# Also save the standard expected filename
pyautogui.screenshot('sf_after_crawl.png')
print("✅ Standard screenshot also saved as sf_after_crawl.png")