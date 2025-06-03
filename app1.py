import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode
import os
import base64
import random
import time
import json
from urllib.parse import quote

async def try_hashnode_specific():
    """Advanced techniques specifically for Hashnode/Vercel sites"""

    # Try different approaches in sequence
    strategies = [
        {
            "name": "Mobile Chrome with Touch",
            "user_agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "args": [
                "--user-agent=Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--touch-events=enabled",
                "--mobile-emulation",
            ]
        },
        {
            "name": "Slow Human Simulation",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--exclude-switches=enable-automation",
                "--disable-extensions",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1366,768",
                "--start-maximized"
            ]
        },
        {
            "name": "Firefox Simulation",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-features=TranslateUI"
            ]
        }
    ]

    target_url = 'https://kasenda.hashnode.dev/whats-new-and-migration-guide-tailwind-css-v40'

    for strategy in strategies:
        print(f"\n🔄 Trying: {strategy['name']}")

        try:
            async with AsyncWebCrawler(
                headless=True,
                verbose=True,
                user_agent=strategy["user_agent"],
                browser_args=strategy["args"],
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            ) as crawler:

                # Random human-like delay
                await asyncio.sleep(random.uniform(3, 7))

                result = await crawler.arun(
                    url=target_url,
                    cache_mode=CacheMode.BYPASS,
                    delay_before_return_html=random.uniform(8, 15),  # Longer delay
                    screenshot=True,
                    screenshot_config={"full_page": True},
                    html2text={
                        "ignore_links": False,
                        "body_width": 0
                    },
                    # Advanced options
                    simulate_user=True,
                    override_navigator=True,
                    process_iframes=True,
                    remove_overlay_elements=True,
                    # Wait for content to load
                    wait_for_images=False,
                    js_code=[
                        # Execute JavaScript to bypass some checks
                        "window.navigator.webdriver = undefined;",
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
                        "delete window.navigator.webdriver;",
                        # Scroll to trigger lazy loading
                        "window.scrollTo(0, document.body.scrollHeight/2);",
                        "window.scrollTo(0, 0);"
                    ]
                )

                if result.success:
                    content = result.markdown.raw_markdown
                    print(f"Content length: {len(content)}")

                    # Check for success indicators
                    if len(content) > 1000 and any(keyword in content.lower() for keyword in
                        ['tailwind css', 'migration guide', 'v4.0', 'new features', 'whats new']):

                        print(f"🎉 SUCCESS with {strategy['name']}!")

                        # Save the content
                        filename = f"hashnode_tailwind_v4_{strategy['name'].lower().replace(' ', '_')}.md"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)

                        print(f"✅ Content saved to: {filename}")
                        print(f"📄 Content preview:\n{'-'*50}")
                        print(content[:800] + "...")
                        print("-" * 50)

                        # Save screenshot if available
                        if result.screenshot:
                            screenshot_data = base64.b64decode(result.screenshot)
                            screenshot_path = f"hashnode_screenshot_{strategy['name'].lower().replace(' ', '_')}.png"
                            with open(screenshot_path, "wb") as f:
                                f.write(screenshot_data)
                            print(f"📸 Screenshot saved: {screenshot_path}")

                        return True

                    elif "vercel security checkpoint" in content.lower():
                        print(f"❌ Still blocked by security checkpoint with {strategy['name']}")
                        print(f"Response: {content[:200]}")

                    else:
                        print(f"⚠️ Got response but content seems incomplete")
                        print(f"Content sample: {content[:300]}")

                else:
                    print(f"❌ Request failed: {result.error}")

        except Exception as e:
            print(f"❌ Exception with {strategy['name']}: {str(e)}")
            continue

    return False

async def try_alternative_methods():
    """Try alternative methods to get the content"""

    print("\n🔍 Trying alternative methods...")

    # Method 1: Try Google Cache
    google_cache_url = f"https://webcache.googleusercontent.com/search?q=cache:https://kasenda.hashnode.dev/whats-new-and-migration-guide-tailwind-css-v40"

    # Method 2: Try Archive.org
    archive_urls = [
        "https://web.archive.org/web/20241201000000*/https://kasenda.hashnode.dev/whats-new-and-migration-guide-tailwind-css-v40",
        "https://archive.today/https://kasenda.hashnode.dev/whats-new-and-migration-guide-tailwind-css-v40"
    ]

    # Method 3: Try Hashnode API (if available)
    # Hashnode has a GraphQL API - we might be able to get the content directly
    api_url = "https://gql.hashnode.com/"

    all_urls = [google_cache_url] + archive_urls

    async with AsyncWebCrawler(
        headless=True,
        verbose=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ) as crawler:

        for i, url in enumerate(all_urls):
            print(f"\n🔄 Trying alternative method {i+1}: {url[:60]}...")

            try:
                result = await crawler.arun(
                    url=url,
                    cache_mode=CacheMode.BYPASS,
                    delay_before_return_html=5,
                    html2text={"ignore_links": False, "body_width": 0}
                )

                if result.success:
                    content = result.markdown.raw_markdown
                    if len(content) > 1000 and 'tailwind' in content.lower():
                        print(f"🎉 SUCCESS with alternative method!")

                        filename = f"hashnode_alternative_method_{i+1}.md"
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(content)

                        print(f"✅ Content saved to: {filename}")
                        return True
                    else:
                        print(f"⚠️ Got response but content seems limited")
                else:
                    print(f"❌ Failed: {result.error}")

            except Exception as e:
                print(f"❌ Exception: {str(e)}")
                continue

    return False

async def manual_instructions():
    """Provide manual workaround instructions"""
    print("\n" + "="*60)
    print("🔧 MANUAL WORKAROUND SUGGESTIONS:")
    print("="*60)

    instructions = """
    If automated methods fail, here are manual options:

    1. 🌐 Use a VPN:
       - Connect to a different country
       - Try the URL again

    2. 🔄 Browser Developer Tools:
       - Open Chrome/Firefox
       - Go to the URL manually
       - Once loaded, right-click → View Page Source
       - Copy the HTML content

    3. 📱 Try Different Networks:
       - Use mobile data instead of WiFi
       - Try from a different location

    4. 🤖 Use Browser Extensions:
       - Install "User-Agent Switcher"
       - Try different user agents

    5. 📧 Contact the Author:
       - Reach out to the Hashnode author directly
       - Ask for the content or a PDF version

    6. 🔍 Search for Mirrors:
       - Look for the same content on other platforms
       - Check if it's cross-posted anywhere
    """

    print(instructions)

async def main():
    print("🎯 Targeting Hashnode article specifically...")

    # Try advanced strategies
    success = await try_hashnode_specific()

    if not success:
        print("\n" + "="*50)
        print("Primary methods failed. Trying alternatives...")
        success = await try_alternative_methods()

    if not success:
        await manual_instructions()
        print("\n❌ All automated methods failed.")
        print("The Hashnode article has strong bot protection.")
        print("Consider using the manual workarounds above.")
    else:
        print("\n🎉 Successfully retrieved the Hashnode article!")

if __name__ == "__main__":
    asyncio.run(main())