"""
Modular Bing Image Scraper with Enhanced Browser Management and Magic Prompt Enhancement
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

# Hugging Face imports for prompt enhancement
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

from seleniumbase import SB
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions


class PromptEnhancer:
    """
    Magic Prompt Enhancer using Hugging Face's Flux-Prompt-Enhance model.
    Similar to Ideogram's Magic Prompt feature.
    """
    
    def __init__(self):
        self.model_checkpoint = "gokaygokay/Flux-Prompt-Enhance"
        self.max_target_length = 256
        self.prefix = "enhance prompt: "
        self.enhancer = None
        self.model = None
        self.tokenizer = None
        self.device = 0 if torch.cuda.is_available() else -1
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the prompt enhancement model."""
        spinner = SpinnerAnimation("Loading Magic Prompt Enhancer")
        spinner.start()
        
        try:
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_checkpoint)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_checkpoint)
            
            # Create the Hugging Face text2text-generation pipeline
            self.enhancer = pipeline(
                "text2text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                repetition_penalty=1.2,
                device=self.device  # 0 for CUDA, -1 for CPU
            )
            
            device_type = "GPU (CUDA)" if self.device == 0 else "CPU"
            spinner.stop(f"✓ Magic Prompt Enhancer loaded successfully on {device_type}")
            
        except Exception as e:
            spinner.stop(f"✗ Failed to load Magic Prompt Enhancer: {str(e)}")
            print("⚠ Continuing without prompt enhancement...")
            self.enhancer = None
    
    def enhance_prompt(self, prompt: str) -> str:
        """
        Enhance the provided prompt using the Flux-Prompt-Enhance model.
        Returns the enhanced prompt, or the original prompt if enhancement fails.
        """
        if not self.enhancer:
            print("⚠ Prompt enhancer not available, using original prompt")
            return prompt
        
        try:
            print(f"🔮 Enhancing prompt: '{prompt}'")
            response = self.enhancer(
                self.prefix + prompt, 
                max_length=self.max_target_length
            )
            enhanced_prompt = response[0]['generated_text']
            
            print(f"✨ Enhanced prompt: '{enhanced_prompt}'")
            return enhanced_prompt
            
        except Exception as e:
            print(f"⚠ Prompt enhancement failed: {str(e)}")
            print("Using original prompt instead...")
            return prompt
    
    def is_available(self) -> bool:
        """Check if the prompt enhancer is available."""
        return self.enhancer is not None


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
    
    def __init__(self, cookies_file: str = "src\\cookies.json"):
        self.cookies_file = Path(cookies_file)
    
    def save_cookies(self, sb_instance) -> bool:
        """Save current browser cookies to file."""
        try:
            cookies = sb_instance.get_cookies()
            # Ensure the directory exists
            self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
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
        named after the prompt. The folder name is generated in kebab-case
        and truncated to a maximum length if necessary.
        """
        # Convert the prompt to a valid kebab-case folder name.
        folder_name = self.to_kebab_case(prompt)
        # Set maximum folder name length (adjust as necessary)
        max_length = 50
        if len(folder_name) > max_length:
            folder_name = folder_name[:max_length]
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
            # Generate a random hash-based filename.
            import uuid  # Consider placing this import at the top of your file.
            random_hash = uuid.uuid4().hex
            filename = f"{random_hash}.{ext}"
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
        spinner = SpinnerAnimation(f"Generating images for: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'")
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
    Main scraper class that orchestrates all components with Magic Prompt Enhancement.
    """
    
    headless: bool = True
    undetected: bool = True
    browser: str = "chrome"  # "chrome" or "edge"
    cookies_file: str = "src\\cookies.json"
    output_dir: str = "outputs"
    timeout: int = 60
    enable_prompt_enhancement: bool = True  # New parameter for prompt enhancement
    
    def __post_init__(self):
        """Initialize scraper components."""
        self.sb: Optional[SB] = None
        self.cookie_manager = CookieManager(self.cookies_file)
        self.image_processor = ImageProcessor(self.output_dir)
        self.auth_manager = None
        self.image_generator = None
        
        # Initialize prompt enhancer if enabled
        if self.enable_prompt_enhancement:
            self.prompt_enhancer = PromptEnhancer()
        else:
            self.prompt_enhancer = None
    
    def _get_browser_config(self) -> Dict[str, Any]:
        """Get SeleniumBase configuration with proper browser options."""
        config = {
            "browser": self.browser.lower(),
            "headless": self.headless,
            "undetected": self.undetected,
            "incognito": True,
            "disable_csp": True,
            "block_images": False,
        }
        
        return config
    
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
    
    def get_user_prompt(self) -> Optional[str]:
        """Get prompt from user with enhancement options."""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("🎨 Image Generation with Magic Prompt Enhancement")
        print("=" * 50)
        
        # Show enhancement status
        if self.prompt_enhancer and self.prompt_enhancer.is_available():
            print("✨ Magic Prompt Enhancement: ENABLED")
        else:
            print("⚠ Magic Prompt Enhancement: DISABLED")
        
        print()
        prompt = input("Enter your image prompt: ").strip()
        
        if not prompt:
            print("⚠ Empty prompt provided")
            return None
        
        # Ask user if they want to enhance the prompt (if enhancer is available)
        if self.prompt_enhancer and self.prompt_enhancer.is_available():
            print("\nOptions:")
            print("1. Use Magic Prompt Enhancement (recommended)")
            print("2. Use original prompt as-is")
            
            choice = input("\nChoose option (1/2, default: 1): ").strip()
            
            if choice != "2":
                return self.prompt_enhancer.enhance_prompt(prompt)
            else:
                print("Using original prompt without enhancement")
                return prompt
        else:
            return prompt
    
    def run_generation_cycle(self) -> bool:
        """Run a complete image generation and download cycle with prompt enhancement."""
        try:
            # Get and potentially enhance prompt from user
            prompt = self.get_user_prompt()
            
            if not prompt:
                return False
            
            print(f"\n🚀 Starting image generation...")
            print(f"📝 Final prompt: '{prompt}'")
            print()
            
            # Generate images using the (potentially enhanced) prompt
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
        print("🚀 Starting Enhanced Bing Image Scraper with Magic Prompt...")
        print("=" * 60)
        
        config = self._get_browser_config()
        
        # Use the 'with' block to properly enter and exit the SB context manager.
        with SB(**config) as sb:
            self.sb = sb
            
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

        print("\n👋 Enhanced Scraper session ended")
    
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
    print("🎯 Enhanced Bing Image Scraper with Magic Prompt Enhancement")
    print("=" * 60)
    print("📦 Installing required packages...")
    print("Run: pip install transformers torch seleniumbase")
    print()
    
    # Create scraper instance with your settings
    scraper = BingImageScraper(
        headless=True,                      # Set to True for headless operation
        undetected=True,                    # Use undetected mode
        browser="chrome",                   # "chrome" or "edge"
        output_dir="outputs",               # Output directory for images
        timeout=60,                         # Generation timeout in seconds
        enable_prompt_enhancement=True      # Enable Magic Prompt Enhancement
    )
    
    # Start the scraping process
    scraper.start()
    
    # At the end of the run, overwrite (update) the cookies file
    scraper.cleanup()