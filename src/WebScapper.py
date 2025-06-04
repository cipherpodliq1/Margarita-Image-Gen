"""
Modular Bing Image Scraper with Enhanced Browser Management
"""

import os
import time
import json
import requests
import threading
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import base64
from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


class SpinnerAnimation:
    """
    Animated loading spinner for visual feedback during operations.
    """
    
    def __init__(self, message: str = "Loading", spinner_chars: str = "|/-\\"):
        self.message = message
        self.spinner_chars = spinner_chars
        self.is_spinning = False
        self.thread = None
    
    def _spin(self):
        """Internal method to animate the spinner."""
        i = 0
        while self.is_spinning:
            print(f"\r{self.message}... {self.spinner_chars[i % len(self.spinner_chars)]}", 
                  end="", flush=True)
            time.sleep(0.1)
            i += 1
    
    def start(self):
        """Start the spinner animation."""
        self.is_spinning = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self, final_message: str = None):
        """Stop the spinner animation."""
        self.is_spinning = False
        if self.thread:
            self.thread.join()
        
        # Clear the spinner line
        print("\r" + " " * (len(self.message) + 10), end="")
        print(f"\r{final_message or '✓ Complete'}")


class BrowserConfig:
    """
    Browser configuration manager for different browser types.
    """
    
    @staticmethod
    def get_chrome_options(headless: bool = True, undetected: bool = True) -> ChromeOptions:
        """Get optimized Chrome options."""
        options = ChromeOptions()
        
        # Basic stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        if headless:
            options.add_argument('--headless')
        
        if undetected:
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        return options
    
    @staticmethod
    def get_edge_options(headless: bool = True, undetected: bool = True) -> EdgeOptions:
        """Get optimized Edge options."""
        options = EdgeOptions()
        
        # Basic stealth options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        if headless:
            options.add_argument('--headless')
        
        if undetected:
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent
        options.add_argument(
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 '
            'Edg/120.0.0.0'
        )
        
        return options


class CookieManager:
    """
    Manages browser cookies for persistent authentication.
    """
    
    def __init__(self, cookies_file: str = "src\cookies.json"):
        self.cookies_file = Path(cookies_file)
    
    def save_cookies(self, sb_instance) -> bool:
        """Save current browser cookies to file."""
        try:
            cookies = sb_instance.get_cookies()
            with open(self.cookies_file, 'w+') as f:
                json.dump(cookies, f, indent=2)
            print(f"✓ Cookies saved to {self.cookies_file}")
            return True
        except Exception as e:
            print(f"✗ Failed to save cookies: {str(e)}")
            return False
    
    def load_cookies(self, sb_instance) -> bool:
        """Load previously saved cookies."""
        if not self.cookies_file.exists():
            print("ℹ No saved cookies found")
            return False

        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # Navigate to the base domain before adding cookies.
            print("Navigating to https://www.bing.com ...")
            sb_instance.open("https://www.bing.com/images/create/")
            time.sleep(3)  # Wait for the page to load completely.

            for cookie in cookies:
                # Convert "expires" to "expiry" if needed.
                if 'expires' in cookie:
                    cookie['expiry'] = cookie.pop('expires')
                
                # Adjust domain if it starts with a dot.
                if cookie.get("domain", "").startswith("."):
                    cookie["domain"] = "www.bing.com"
                
                # Keep only the allowed keys for Selenium.
                allowed_keys = {"name", "value", "path", "domain", "secure", "expiry"}
                filtered_cookie = {k: cookie[k] for k in cookie if k in allowed_keys}

                try:
                    sb_instance.add_cookie(filtered_cookie)
                except Exception as e:
                    print(f"⚠ Warning: Could not add cookie {filtered_cookie.get('name', 'unknown')}: {str(e)}")
            
            return True
        except Exception as e:
            print(f"✗ Failed to load cookies: {str(e)}")
            return False


class AuthenticationManager:
    """
    Handles user authentication for Bing Image Creator.
    """
    
    def __init__(self, sb_instance, cookie_manager: CookieManager):
        self.sb = sb_instance
        self.cookie_manager = cookie_manager
        self.page_url = "https://www.bing.com/create"
    
    
    def _get_prompt_input_element(self):
        """Find and return the prompt input element, searching in default content 
           and then in all available iframes if necessary."""
        # Try default context first using the known CSS selector.
        try:
            element = self.sb.wait_for_element_present("#gi_form_q", timeout=5)
            return element
        except Exception as e:
            print("Element not found in default content; searching in iframes...")
        
        # Get all iframes on the page.
        iframes = self.sb.driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                self.sb.driver.switch_to.frame(iframe)
                # Attempt to locate the element inside the iframe.
                element = self.sb.wait_for_element_present("#gi_form_q", timeout=5)
                return element  # Found the element; remain in this frame.
            except Exception:
                # Switch back to the default context before trying the next frame.
                self.sb.driver.switch_to.default_content()
                continue
        
        # If the element was not found in any iframe, switch back to default and throw an error.
        self.sb.driver.switch_to.default_content()
        raise Exception("Could not locate prompt input element in default content or any iframes.")
    
    def authenticate(self) -> bool:
        """Complete authentication process using cookies."""
        print("🔐 Starting cookie-based authentication...")
        
        # Load cookies and assume authentication works if cookies are loaded.
        if self.cookie_manager.load_cookies(self.sb):
            self.sb.refresh()
            time.sleep(3)
            print("✓ Authentication assumed successful using saved cookies")
            return True

        print("❌ Cookie authentication failed")
        print("Please ensure you have a valid cookies.json file with authentication cookies.")
        return False
class ImageProcessor:
    """
    Handles image URL extraction and downloading.
    Downloads images directly into a subfolder named after the prompt.
    """

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case for naming directories and files."""
        text = re.sub(r'[^\w\s-]', '', text.strip())
        text = re.sub(r'[-\s]+', '-', text)
        return text.lower()

    def prepare_prompt_folder(self, prompt: str) -> Path:
        """
        Creates and returns a subfolder within the output directory,
        named after the prompt.
        """
        folder_name = self.to_kebab_case(prompt)
        prompt_folder = self.output_dir / folder_name
        prompt_folder.mkdir(exist_ok=True)
        return prompt_folder

    def get_image_urls(self, sb_instance) -> List[str]:
        """
        Polls for image URLs from the generated results page.
        Waits an extra 10 seconds for all images to load.
        Then polls every 2 seconds (up to 60 seconds) until at least 4 valid URLs are found.
        A URL is considered valid if it starts with "http" or "blob:".
        Returns exactly 4 URLs (padding with empty strings if necessary).
        """
        print("Extracting image URLs...")
        time.sleep(10)
        start_time = time.time()
        poll_timeout = 60  # seconds
        urls = []
        while time.time() - start_time < poll_timeout:
            image_elements = sb_instance.find_elements(By.CSS_SELECTOR, "img.image-row-img")
            urls = []
            for elem in image_elements:
                src = elem.get_attribute("src")
                if src and (src.startswith("http") or src.startswith("blob:")) and src not in urls:
                    urls.append(src)
            if len(urls) >= 4:
                break
            time.sleep(2)
        print(f"Found {len(urls)} valid image URLs after polling.")
        while len(urls) < 4:
            urls.append("")
        return urls[:4]

    def download_image(self, sb_instance, image_url: str, prompt: str, index: int) -> Optional[str]:
        """
        Downloads a single image by extracting the blob contents in the browser.
        Instead of opening the blob URL, we do the following:
          - Execute JS in the browser to fetch the blob from the blob URL.
          - Convert the blob to a base64-encoded data URL.
          - Return the base64 string to Python.
          - Decode it and save as a file.
        Returns the file path as a string on success, or None on failure.
        """
        if not image_url:
            print(f"Skipping image {index+1} - no URL available")
            return None

        print(f"Downloading image {index+1} from blob URL: {image_url}")
        try:
            # JavaScript to fetch the blob, convert to base64 data URL, and return it.
            js_script = f"""
            const url = "{image_url}";
            return fetch(url)
                .then(response => response.blob())
                .then(blob => new Promise((resolve, reject) => {{
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result);
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                }}));
            """
            data_url = sb_instance.execute_script(js_script)
            if not data_url:
                print(f"Could not retrieve data from blob for image {index+1}")
                return None

            # Data URL looks like: "data:image/png;base64,AAA..."
            header, base64_data = data_url.split(',', 1)
            # Choose extension based on MIME type.
            mime_type = header.split(';')[0].split(':')[1]
            ext = {
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
            }.get(mime_type, "png")

            prompt_folder = self.prepare_prompt_folder(prompt)
            filename = f"{self.to_kebab_case(prompt)}-{index+1}.{ext}"
            filepath = prompt_folder / filename

            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))
            print(f"Image {index+1} saved as {filename} in folder {prompt_folder}")
            return str(filepath)
        except Exception as e:
            print(f"Failed to download image {index+1}: {str(e)}")
            return None

    def download_all_images(self, sb_instance, image_urls: List[str], prompt: str) -> List[str]:
        """
        Downloads all images from the list of image URLs.
        Returns a list of file paths of the downloaded images.
        """
        valid_urls = [url for url in image_urls if url]
        print(f"Starting download of {len(valid_urls)} images...")
        downloaded_files = []
        for i, url in enumerate(image_urls):
            if url:
                path = self.download_image(sb_instance, url, prompt, i)
                if path:
                    downloaded_files.append(path)
                time.sleep(2)
        print(f"Successfully downloaded {len(downloaded_files)} images.")
        return downloaded_files

class ImageGenerator:
    """
    Handles the image generation process on Bing Image Creator.
    """
    
    def __init__(self, sb_instance, timeout: int = 60):
        self.sb = sb_instance
        self.timeout = timeout
        self.page_url = "https://www.bing.com/create"
    
    def switch_to_prompt_frame(self) -> bool:
        """
        Switches to the frame that contains the prompt input element.
        Returns True if the element is found; otherwise, returns False.
        """
        # Start from default content.
        self.sb.driver.switch_to.default_content()
        if self.sb.is_element_present("#gi_form_q"):
            return True
        
        # Iterate over all iframes.
        iframes = self.sb.driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                self.sb.driver.switch_to.frame(iframe)
                if self.sb.is_element_present("#gi_form_q"):
                    return True
            except Exception:
                pass
            self.sb.driver.switch_to.default_content()
        
        self.sb.driver.switch_to.default_content()
        return False

    def switch_to_create_button_frame(self) -> bool:
        """
        Switches to the frame that contains the create button.
        Returns True if the create button is found; otherwise, returns False.
        """
        # Start from default content.
        self.sb.driver.switch_to.default_content()
        if self.sb.is_element_present("#create_btn_c"):
            return True
        
        # Iterate over all iframes.
        iframes = self.sb.driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                self.sb.driver.switch_to.frame(iframe)
                if self.sb.is_element_present("#create_btn_c"):
                    return True
            except Exception:
                pass
            self.sb.driver.switch_to.default_content()
        
        self.sb.driver.switch_to.default_content()
        return False

    def generate_image(self, prompt: str) -> bool:
        """Generate images using the provided text prompt."""
        spinner = SpinnerAnimation(f"Generating images for: '{prompt}'")
        spinner.start()
        
        try:
            # Navigate to the main page.
            self.sb.open(self.page_url)
            time.sleep(3)
            
            # Switch to the frame containing the prompt input element.
            if not self.switch_to_prompt_frame():
                spinner.stop("✗ Prompt input element not found in any frame")
                return False
            
            # Clear and fill the prompt input using the CSS selector.
            self.sb.clear("#gi_form_q")
            self.sb.type("#gi_form_q", prompt)
            
            # Now search for the create button in all iframes.
            if not self.switch_to_create_button_frame():
                spinner.stop("✗ Create button not found in any frame")
                return False
            
            # Directly click the create button using its CSS selector.
            self.sb.click("#create_btn_c")
            
            spinner.stop("⏳ Waiting for image generation...")
            
            # Wait for images to be generated using one of the expected completion selectors.
            generation_spinner = SpinnerAnimation("Waiting for images to generate")
            generation_spinner.start()
            
            completion_selectors = [
                "a[href*='create'][href*='id=']",
                "ul li div div a[href*='create']",
                ".gir_mmimg a[href*='create']"
            ]
            
            for selector in completion_selectors:
                try:
                    self.sb.wait_for_element_present(selector, timeout=self.timeout)
                    print("Sleeping for 10 seconds...")
                    time.sleep(10)
                    generation_spinner.stop("✓ Images generated successfully")
                    return True
                except Exception:
                    continue
            
            # Fallback: try a generic XPath for completion.
            try:
                self.sb.wait_for_element_present("xpath://a[contains(@href, 'create') and contains(@href, 'id=')]",
                                                   timeout=self.timeout)
                generation_spinner.stop("✓ Images generated successfully")
                return True
            except Exception:
                pass
            
            generation_spinner.stop("✗ Image generation timeout or failed")
            return False
            
        except Exception as e:
            spinner.stop(f"✗ Image generation failed: {str(e)}")
            return False


@dataclass
class BingImageScraper:
    """
    Main scraper class that orchestrates all components.
    """
    
    headless: bool = True
    undetected: bool = True
    browser: str = "chrome"  # "chrome" or "edge"
    cookies_file: str = "src\cookies.json"
    output_dir: str = "outputs"
    timeout: int = 60
    
    def __post_init__(self):
        """Initialize scraper components."""
        self.sb: Optional[SB] = None
        self.cookie_manager = CookieManager(self.cookies_file)
        self.image_processor = ImageProcessor(self.output_dir)
        self.auth_manager = None
        self.image_generator = None
    
    def _get_browser_config(self) -> Dict[str, Any]:
        """Get SeleniumBase configuration with proper browser options."""
        config = {
            "browser": self.browser.lower(),
            "headless": self.headless,
            "undetected": self.undetected,
            "incognito": True,
            "disable_csp": True,
            "block_images": False,
            #"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        return config
    
    def start_browser(self) -> None:
        """Initialize and configure the browser."""
        spinner = SpinnerAnimation("Initializing browser")
        spinner.start()
        
        try:
            config = self._get_browser_config()
            self.sb = SB(**config)
            self.sb.open("https://www.bing.com/create")
            
            # Initialize managers with SB instance
            self.auth_manager = AuthenticationManager(self.sb, self.cookie_manager)
            self.image_generator = ImageGenerator(self.sb, self.timeout)
            
            # Handle cookie consent if present
            self._handle_cookie_consent()
            
            spinner.stop("✓ Browser initialized successfully")
            
        except Exception as e:
            spinner.stop(f"✗ Failed to initialize browser: {str(e)}")
            raise
    
    def _handle_cookie_consent(self) -> None:
        """Handle cookie consent popup."""
        try:
            self.sb.wait_for_element_present(
                "button[id*='accept'], button[class*='accept']", 
                timeout=3
            )
            self.sb.click("button[id*='accept'], button[class*='accept']")
            print("✓ Cookie consent handled")
            time.sleep(2)
        except Exception:
            pass
    
    def run_generation_cycle(self) -> bool:
        """Run a complete image generation and download cycle."""
        try:
            # Get prompt from user
            os.system('cls' if os.name == 'nt' else 'clear')
            prompt = input("🎨 Enter your image prompt: ").strip()
            
            if not prompt:
                print("⚠ Empty prompt provided")
                return False
            
            # Generate images
            if not self.image_generator.generate_image(prompt):
                return False
            
            # Get image URLs
            image_urls = self.image_processor.get_image_urls(self.sb)
            if not any(image_urls):
                print("✗ No image URLs found")
                return False
            
            
        
            # Download images
            downloaded_files = self.image_processor.download_all_images(
                self.sb, image_urls, prompt
            )
            
            if downloaded_files:
                print(f"\n🎉 Generation cycle completed successfully!")
                print(f"📁 {len(downloaded_files)} images saved to '{self.output_dir}' directory")
                return True
            else:
                print("✗ No images were downloaded")
                return False
                
        except Exception as e:
            print(f"✗ Generation cycle failed: {str(e)}")
            return False
    
    def start(self) -> None:
        print("🚀 Starting Bing Image Scraper...")
        print("=" * 50)
        config = self._get_browser_config()
        # Use the 'with' block to properly enter and exit the SB context manager.
        with SB(**config) as sb:
            self.sb = sb  # Now sb has the expected methods like open(), get_cookies(), etc.
            
            # Initialize managers with the entered SB instance
            self.auth_manager = AuthenticationManager(self.sb, self.cookie_manager)
            self.image_generator = ImageGenerator(self.sb, self.timeout)
            
            # Handle cookie consent if present
            self._handle_cookie_consent()

            # Authenticate user
            if not self.auth_manager.authenticate():
                print("❌ Authentication failed. Cannot proceed.")
                return

            # Main generation loop
            while True:
                try:
                    success = self.run_generation_cycle()

                    if success:
                        # Ask if user wants to continue
                        continue_choice = input("\n🔄 Generate another image? (y/n): ").strip().lower()
                        if continue_choice not in ['y', 'yes']:
                            break
                    else:
                        retry_choice = input("\n🔄 Generation failed. Try again? (y/n): ").strip().lower()
                        if retry_choice not in ['y', 'yes']:
                            break

                except KeyboardInterrupt:
                    print("\n⏹ Generation interrupted by user")
                    break
                except Exception as e:
                    print(f"\n❌ Unexpected error in generation loop: {str(e)}")
                    break

            # When the 'with' block exits, __exit__ is automatically called to quit the browser.
        print("\n👋 Scraper session ended")
    
    def cleanup(self) -> None:
        """Clean up resources by saving/updating cookies and then closing the browser."""
        try:
            if self.sb:
                print("Saving cookies before closing browser...")
                # Attempt to save (i.e. overwrite) cookies.
                cookie_saved = self.cookie_manager.save_cookies(self.sb)
                if cookie_saved:
                    print("✓ Cookies updated successfully.")
                else:
                    print("⚠ Failed to update cookies.")
                self.sb.quit()
                print("✓ Browser closed successfully.")
            else:
                print("No browser instance found. Nothing to clean up.")
        except Exception as e:
            print(f"⚠ Error during cleanup: {str(e)}")
        finally:
            print("\n👋 Scraper session ended")


if __name__ == "__main__":
    # Create scraper instance with your settings
    scraper = BingImageScraper(
        headless=True,           # Set to True for headless operation
        undetected=True,         # Use undetected mode
        browser="chrome",        # "chrome" or "edge"
        output_dir="outputs",    # Output directory for images
        timeout=60               # Generation timeout in seconds
    )
    
    # Start the scraping process
    scraper.start()
    
    # At the end of the run, overwrite (update) the cookies file
    scraper.cleanup()