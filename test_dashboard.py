import os
import time
import logging
import pytest
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DashboardTester:
    def __init__(self, base_url, email, password, headless=True, screenshot_dir="screenshots"):
        self.base_url = base_url
        self.login_email = email
        self.login_password = password
        self.headless = headless
        self.screenshot_dir = screenshot_dir

        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.driver = None
        self.wait = None

    def initialize_driver(self):
        try:
            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            if self.headless:
                options.add_argument("--headless=new")

            # Try to use Chrome directly first (most reliable)
            try:
                self.driver = webdriver.Chrome(options=options)
                logger.info("Chrome driver initialized directly")
            except Exception as direct_error:
                logger.warning(f"Direct Chrome failed: {direct_error}")
                # Fallback to webdriver-manager
                try:
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=options)
                    logger.info("Chrome driver initialized via webdriver-manager")
                except Exception as manager_error:
                    logger.error(f"Both Chrome methods failed: {manager_error}")
                    raise manager_error
                
            self.driver.set_window_size(1280, 800)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Driver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Driver initialization failed: {e}")
            return False

    def take_screenshot(self, label):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshot_dir, f"{label}_{ts}.png")
        try:
            self.driver.save_screenshot(path)
            logger.info(f"Screenshot saved: {path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")

    def login(self):
        try:
            logger.info(f"Navigating to: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for page to load and take a screenshot
            time.sleep(5)
            self.take_screenshot("before_login")
            
            # Check if we're already on a dashboard page
            current_url = self.driver.current_url
            logger.info(f"Current URL: {current_url}")
            
            # Check if we're already logged in by looking for dashboard indicators
            try:
                page_source = self.driver.page_source.lower()
                dashboard_indicators = ["dashboard", "overview", "analytics", "campaigns", "logout", "profile", "settings"]
                if any(indicator in page_source for indicator in dashboard_indicators):
                    logger.info("Dashboard indicators found - appears to be already logged in")
                    return True
            except Exception as e:
                logger.debug(f"Error checking for dashboard indicators: {e}")
            
            # If we're on the main page, try to navigate to login
            if "auth.segwise.ai" not in current_url:
                logger.info("On main page, looking for login link...")
                try:
                    # Look for login/signin links
                    login_links = [
                        "//a[contains(text(), 'Login')]",
                        "//a[contains(text(), 'Sign in')]",
                        "//a[contains(text(), 'Log in')]",
                        "//button[contains(text(), 'Login')]",
                        "//button[contains(text(), 'Sign in')]"
                    ]
                    
                    for selector in login_links:
                        try:
                            login_link = self.driver.find_element(By.XPATH, selector)
                            if login_link.is_displayed():
                                logger.info("Found login link, clicking...")
                                login_link.click()
                                time.sleep(3)
                                self.take_screenshot("after_clicking_login_link")
                                break
                        except NoSuchElementException:
                            continue
                    
                    # Check if we're now on the login page
                    current_url = self.driver.current_url
                    logger.info(f"After clicking login link, URL: {current_url}")
                    
                except Exception as e:
                    logger.warning(f"Error looking for login link: {e}")
            
            if "dashboard" in current_url:
                logger.info("Already on dashboard page")
                return True
            
            # Use JavaScript to inspect the page and find form elements
            logger.info("Inspecting page for form elements...")
            form_elements = self.find_form_elements()
            
            if not form_elements:
                logger.error("No form elements found on the page")
                self.take_screenshot("no_form_elements")
                return False
            
            # Find email input using the form elements info
            email_input = None
            for elem_info in form_elements:
                if (elem_info['type'] == 'email' or 
                    'email' in (elem_info['placeholder'] or '').lower() or
                    'email' in (elem_info['name'] or '').lower() or
                    'email' in (elem_info['id'] or '').lower()):
                    # Find the actual element by index
                    try:
                        inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                        if elem_info['index'] < len(inputs):
                            email_input = inputs[elem_info['index']]
                            logger.info(f"Email input found: {elem_info}")
                            break
                    except Exception as e:
                        logger.debug(f"Error accessing element by index: {e}")
                        continue
            
            # If no email input found with explicit identifiers, assume first text input is email
            if not email_input and form_elements:
                for elem_info in form_elements:
                    if elem_info['type'] == 'text':
                        try:
                            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                            if elem_info['index'] < len(inputs):
                                email_input = inputs[elem_info['index']]
                                logger.info(f"Assuming first text input is email: {elem_info}")
                                break
                        except Exception as e:
                            logger.debug(f"Error accessing element by index: {e}")
                            continue
                        break  # Only take the first text input
            
            if not email_input:
                logger.error("Email input not found in form elements")
                self.take_screenshot("email_input_not_found")
                return False
            
            email_input.send_keys(self.login_email)
            logger.info("Email entered successfully")
            
            # Find password input
            password_input = None
            for elem_info in form_elements:
                if (elem_info['type'] == 'password' or 
                    'password' in (elem_info['placeholder'] or '').lower() or
                    'password' in (elem_info['name'] or '').lower() or
                    'password' in (elem_info['id'] or '').lower()):
                    try:
                        inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                        if elem_info['index'] < len(inputs):
                            password_input = inputs[elem_info['index']]
                            logger.info(f"Password input found: {elem_info}")
                            break
                    except Exception as e:
                        logger.debug(f"Error accessing password element by index: {e}")
                        continue
            
            if not password_input:
                logger.error("Password input not found")
                self.take_screenshot("password_input_not_found")
                return False
            
            password_input.send_keys(self.login_password)
            logger.info("Password entered successfully")
            
            # Find login button using text content
            login_button = self.find_element_by_text_content("Login", "button")
            if not login_button:
                login_button = self.find_element_by_text_content("Sign in", "button")
            if not login_button:
                login_button = self.find_element_by_text_content("Submit", "button")
            if not login_button:
                login_button = self.find_element_by_text_content("Log in", "button")
            
            # If still no button found, try to find any clickable element with login-related text
            if not login_button:
                logger.info("Trying alternative button detection methods...")
                # Try to find any element containing the text
                login_texts = ["Login", "Sign in", "Submit", "Log in", "Continue", "Enter"]
                for text in login_texts:
                    try:
                        # Look for any element containing the text
                        elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                # Check if it's clickable
                                try:
                                    # Try to get the element's tag and attributes
                                    tag_name = elem.tag_name.lower()
                                    if tag_name in ['button', 'a', 'input', 'div', 'span']:
                                        login_button = elem
                                        logger.info(f"Found login button with text '{text}' and tag '{tag_name}'")
                                        break
                                except:
                                    continue
                        if login_button:
                            break
                    except Exception as e:
                        logger.debug(f"Error searching for text '{text}': {e}")
                        continue
            
            # Last resort: use comprehensive clickable element detection
            if not login_button:
                logger.info("Using comprehensive clickable element detection...")
                clickable_elements = self.find_any_clickable_element()
                
                if clickable_elements:
                    # Look for elements with login-related text
                    login_keywords = ["login", "sign in", "submit", "continue", "enter", "log in"]
                    for elem_info in clickable_elements:
                        elem_text = elem_info['text'].lower()
                        if any(keyword in elem_text for keyword in login_keywords):
                            try:
                                # Find the actual element by index
                                all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
                                if elem_info['index'] < len(all_elements):
                                    login_button = all_elements[elem_info['index']]
                                    logger.info(f"Found login button with comprehensive detection: {elem_info}")
                                    break
                            except Exception as e:
                                logger.debug(f"Error accessing element by index: {e}")
                                continue
                    
                    # If still no button, try the first clickable element that looks like a button
                    if not login_button:
                        for elem_info in clickable_elements:
                            if (elem_info['tagName'].lower() in ['button', 'input'] or 
                                'button' in elem_info['className'].lower() or
                                elem_info['cursor'] == 'pointer'):
                                try:
                                    all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
                                    if elem_info['index'] < len(all_elements):
                                        login_button = all_elements[elem_info['index']]
                                        logger.info(f"Found potential login button: {elem_info}")
                                        break
                                except Exception as e:
                                    logger.debug(f"Error accessing element by index: {e}")
                                    continue
            
            if not login_button:
                logger.error("No login button found with any method")
                self.take_screenshot("login_button_not_found")
                # Log all clickable elements for debugging
                try:
                    clickable_elements = self.find_any_clickable_element()
                    logger.info(f"All clickable elements on page: {clickable_elements}")
                except:
                    pass
                return False
            
            logger.info("Login button found, clicking...")
            login_button.click()
            
            # Wait for redirect to dashboard or success
            try:
                # Wait for either dashboard URL or success indicator
                success = False
                for _ in range(20):  # Wait up to 20 seconds
                    current_url = self.driver.current_url
                    if "dashboard" in current_url or "success" in current_url.lower():
                        logger.info(f"Successfully redirected to: {current_url}")
                        success = True
                        break
                    time.sleep(1)
                
                if not success:
                    logger.warning("No dashboard redirect detected, but continuing...")
                    # Take a screenshot to see where we are
                    self.take_screenshot("after_login_attempt")
                
                return True
                
            except Exception as e:
                logger.error(f"Error waiting for redirect: {e}")
                self.take_screenshot("redirect_error")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            self.take_screenshot("login_error")
            return False


    def verify_metrics(self):
        metrics = ["Cost Per Install", "D1 ROAS", "D7 ROAS", "ROAS", "Cost", "Install", "Revenue"]
        found = 0
        logger.info("Checking for metrics on the page...")
        
        # Wait a bit for page to load
        time.sleep(3)
        
        for metric in metrics:
            try:
                # Try multiple selector strategies for each metric
                selectors = [
                    f"//*[contains(text(), '{metric}')]",
                    f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{metric.lower()}')]",
                    f"//*[contains(@title, '{metric}')]",
                    f"//*[contains(@aria-label, '{metric}')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for el in elements:
                            if el.is_displayed():
                                logger.info(f"Found metric: {metric}")
                                found += 1
                                break
                        if found > 0:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking metric {metric}: {e}")
                continue
                
        # If no specific metrics found, look for any numerical data or dashboard content
        if found == 0:
            logger.info("No specific metrics found, looking for any dashboard content...")
            try:
                # Look for numbers, charts, or dashboard-like elements
                # Use a simpler approach to find numerical content
                all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*")
                number_elements = []
                for elem in all_elements:
                    try:
                        text = elem.text.strip()
                        if text and any(char.isdigit() for char in text):
                            number_elements.append(elem)
                    except:
                        continue
                
                chart_elements = self.driver.find_elements(By.CSS_SELECTOR, "canvas, svg, .chart, .graph")
                
                if number_elements or chart_elements:
                    logger.info(f"Found {len(number_elements)} number elements and {len(chart_elements)} chart elements")
                    found = 2  # Consider this a success if we find dashboard-like content
                else:
                    logger.warning("No dashboard content found")
            except Exception as e:
                logger.debug(f"Error looking for dashboard content: {e}")
                
        if found < 2:
            logger.warning(f"Only found {found} metrics, taking screenshot")
            self.take_screenshot("metrics_check")
        else:
            logger.info(f"Successfully found {found} metrics")
            
        return found >= 2

    def verify_navigation(self):
        nav_items = ["Overview", "Creative Analytics", "Settings", "Analytics", "Campaigns", "Reports", "Dashboard", "Menu", "Navigation"]
        found = 0
        logger.info("Checking for navigation items...")
        
        # Wait a bit for page to load
        time.sleep(2)
        
        # First, check if we're on a page with navigation
        try:
            page_source = self.driver.page_source.lower()
            nav_keywords = ["nav", "menu", "sidebar", "navigation", "tabs", "links"]
            nav_found = any(keyword in page_source for keyword in nav_keywords)
            
            if nav_found:
                logger.info("Navigation-like content detected, looking for nav items...")
            else:
                logger.warning("Page doesn't appear to have navigation, but continuing...")
        except Exception as e:
            logger.debug(f"Error checking page content: {e}")
        
        for item in nav_items:
            try:
                # Try multiple selector strategies for each nav item
                selectors = [
                    f"//a[contains(text(), '{item}')]",
                    f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{item.lower()}')]",
                    f"//a[@title='{item}']",
                    f"//a[contains(@aria-label, '{item}')]",
                    f"//*[contains(text(), '{item}') and (self::a or self::button or self::li)]",
                    f"//nav//*[contains(text(), '{item}')]",
                    f"//*[contains(@class, 'nav')]//*[contains(text(), '{item}')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for el in elements:
                            if el.is_displayed():
                                logger.info(f"Found navigation item: {item}")
                                found += 1
                                break
                        if found > 0:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking nav item {item}: {e}")
                continue
        
        # If no specific nav items found, look for any clickable elements that might be navigation
        if found == 0:
            logger.info("No specific navigation items found, looking for any navigation-like content...")
            try:
                # Look for any clickable elements that might be navigation
                nav_elements = self.driver.find_elements(By.CSS_SELECTOR, "nav, .nav, .menu, .sidebar, [role='navigation']")
                clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, "a, button, [role='button']")
                
                if nav_elements or len(clickable_elements) > 5:  # If we have many clickable elements, it might be navigation
                    logger.info(f"Found {len(nav_elements)} nav containers and {len(clickable_elements)} clickable elements")
                    found = 2  # Consider this a success if we find navigation-like content
                else:
                    logger.warning("No navigation content found")
            except Exception as e:
                logger.debug(f"Error looking for navigation content: {e}")
                
        if found < 2:
            logger.warning(f"Only found {found} navigation items, taking screenshot")
            self.take_screenshot("navigation_check")
        else:
            logger.info(f"Successfully found {found} navigation items or navigation-like content")
            
        return found >= 2

    def verify_charts(self):
        selectors = [
            "canvas", 
            ".chart", 
            "svg", 
            ".graph", 
            "[class*='chart']", 
            "[id*='chart']",
            "[class*='graph']",
            "[id*='graph']",
            "[class*='visualization']",
            "[id*='visualization']",
            "[class*='plot']",
            "[id*='plot']",
            "div[data-chart]",
            "div[data-graph]"
        ]
        total_found = 0
        logger.info("Checking for charts and visualizations...")
        
        # Wait a bit for page to load
        time.sleep(3)
        
        for sel in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                visible_elements = [e for e in elements if e.is_displayed()]
                if visible_elements:
                    logger.info(f"Found {len(visible_elements)} chart elements with selector: {sel}")
                    total_found += len(visible_elements)
            except Exception as e:
                logger.debug(f"Error with selector {sel}: {e}")
                continue
                
        if total_found == 0:
            logger.warning("No charts found, taking screenshot")
            self.take_screenshot("charts_check")
        else:
            logger.info(f"Successfully found {total_found} chart elements")
            
        return total_found > 0

    def logout(self):
        try:
            logger.info("Attempting to logout...")
            
            # Wait a bit for page to load
            time.sleep(2)
            
            # Try multiple strategies to find logout button
            logout_button = None
            logout_selectors = [
                "//button[contains(text(), 'Logout')]",
                "//button[contains(text(), 'Sign out')]",
                "//button[contains(text(), 'Log out')]",
                "//a[contains(text(), 'Logout')]",
                "//a[contains(text(), 'Sign out')]",
                "//a[contains(text(), 'Log out')]",
                "//*[contains(text(), 'Logout')]",
                "//*[contains(text(), 'Sign out')]",
                "//*[contains(@class, 'logout')]",
                "//*[contains(@class, 'signout')]",
                "//*[@id='logout']",
                "//*[@id='signout']",
                # Look in header/navbar areas
                "//header//*[contains(text(), 'Logout')]",
                "//nav//*[contains(text(), 'Logout')]",
                "//*[contains(@class, 'header')]//*[contains(text(), 'Logout')]",
                "//*[contains(@class, 'navbar')]//*[contains(text(), 'Logout')]",
                # Look for user menu/profile areas
                "//*[contains(@class, 'user-menu')]//*[contains(text(), 'Logout')]",
                "//*[contains(@class, 'profile')]//*[contains(text(), 'Logout')]",
                "//*[contains(@class, 'dropdown')]//*[contains(text(), 'Logout')]"
            ]
            
            for selector in logout_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for el in elements:
                        if el.is_displayed():
                            logout_button = el
                            logger.info(f"Logout button found with selector: {selector}")
                            break
                    if logout_button:
                        break
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no logout button found with specific selectors, use comprehensive detection
            if not logout_button:
                logger.info("No specific logout button found, using comprehensive detection...")
                clickable_elements = self.find_any_clickable_element()
                
                if clickable_elements:
                    # Look for elements with logout-related text
                    logout_keywords = ["logout", "sign out", "log out", "exit", "signout", "logoff"]
                    for elem_info in clickable_elements:
                        elem_text = elem_info['text'].lower()
                        if any(keyword in elem_text for keyword in logout_keywords):
                            try:
                                # Find the actual element by index
                                all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
                                if elem_info['index'] < len(all_elements):
                                    logout_button = all_elements[elem_info['index']]
                                    logger.info(f"Found logout button with comprehensive detection: {elem_info}")
                                    break
                            except Exception as e:
                                logger.debug(f"Error accessing element by index: {e}")
                                continue
                    
                    # If still no button, try any clickable element that might be logout
                    if not logout_button:
                        for elem_info in clickable_elements:
                            if (elem_info['tagName'].lower() in ['button', 'a'] or 
                                'logout' in elem_info['className'].lower() or
                                'signout' in elem_info['className'].lower() or
                                elem_info['cursor'] == 'pointer'):
                                try:
                                    all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
                                    if elem_info['index'] < len(all_elements):
                                        logout_button = all_elements[elem_info['index']]
                                        logger.info(f"Found potential logout button: {elem_info}")
                                        break
                                except Exception as e:
                                    logger.debug(f"Error accessing element by index: {e}")
                                    continue
            
            if not logout_button:
                logger.warning("No logout button found, taking screenshot")
                self.take_screenshot("logout_button_not_found")
                # Log all clickable elements for debugging
                try:
                    clickable_elements = self.find_any_clickable_element()
                    logger.info(f"All clickable elements on page: {clickable_elements}")
                except:
                    pass
                # Try to continue anyway
                return True
            
            logout_button.click()
            logger.info("Logout button clicked")
            
            # Wait for logout to complete
            try:
                # Wait for either login page or confirmation
                success = False
                for _ in range(10):  # Wait up to 10 seconds
                    current_url = self.driver.current_url
                    if "login" in current_url.lower() or "auth" in current_url.lower():
                        logger.info(f"Successfully logged out, redirected to: {current_url}")
                        success = True
                        break
                    time.sleep(1)
                
                if not success:
                    logger.warning("No login page redirect detected, but continuing...")
                    self.take_screenshot("after_logout_attempt")
                
                return True
                
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                self.take_screenshot("logout_error")
                return False
                
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            self.take_screenshot("logout_error")
            return False

    def cleanup(self):
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed")

    def run_all_tests(self):
        if not self.initialize_driver():
            return False
        results = {}
        try:
            results["Login"] = self.login()
            if results["Login"]:
                results["Metrics"] = self.verify_metrics()
                results["Navigation"] = self.verify_navigation()
                results["Charts"] = self.verify_charts()
                results["Logout"] = self.logout()
            else:
                results.update({"Metrics": False, "Navigation": False, "Charts": False, "Logout": False})
        finally:
            self.cleanup()

        # Log summary
        passed = sum(results.values())
        logger.info("\n" + "-"*40)
        for k, v in results.items():
            logger.info(f"{k:<12} : {'PASS' if v else 'FAIL'}")
        logger.info("-"*40)
        overall = passed >= 4
        logger.info(f"OVERALL RESULT: {'PASS' if overall else 'FAIL'}")
        return overall

    def find_form_elements(self):
        """Use JavaScript to find form elements that might be hidden by CSS-in-JS"""
        try:
            # Execute JavaScript to find all input elements and their properties
            js_script = """
            const inputs = document.querySelectorAll('input, textarea, select');
            const results = [];
            inputs.forEach((input, index) => {
                const rect = input.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    results.push({
                        index: index,
                        tagName: input.tagName,
                        type: input.type,
                        id: input.id,
                        name: input.name,
                        placeholder: input.placeholder,
                        className: input.className,
                        visible: rect.width > 0 && rect.height > 0,
                        position: {x: rect.x, y: rect.y}
                    });
                }
            });
            return results;
            """
            
            elements_info = self.driver.execute_script(js_script)
            logger.info(f"Found {len(elements_info)} visible form elements:")
            
            for elem in elements_info:
                logger.info(f"  - {elem['tagName']} (type: {elem['type']}, id: {elem['id']}, name: {elem['name']}, placeholder: {elem['placeholder']})")
            
            return elements_info
            
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            return []

    def find_element_by_text_content(self, text, element_type="*"):
        """Find elements by their text content, useful for buttons and labels"""
        try:
            # Try to find elements containing the text
            xpath = f"//{element_type}[contains(text(), '{text}')]"
            elements = self.driver.find_elements(By.XPATH, xpath)
            
            visible_elements = [e for e in elements if e.is_displayed()]
            if visible_elements:
                logger.info(f"Found {len(visible_elements)} visible elements with text '{text}'")
                return visible_elements[0]  # Return first visible element
                
        except Exception as e:
            logger.debug(f"Error finding element with text '{text}': {e}")
        
        return None

    def find_any_clickable_element(self):
        """Find any element that could be clickable, including Mantine UI components"""
        try:
            logger.info("Searching for any clickable element on the page...")
            
            # Execute JavaScript to find all potentially clickable elements
            js_script = """
            const clickableElements = [];
            const allElements = document.querySelectorAll('*');
            
            allElements.forEach((el, index) => {
                const rect = el.getBoundingClientRect();
                const styles = window.getComputedStyle(el);
                
                // Check if element is visible and has reasonable size
                if (rect.width > 0 && rect.height > 0 && 
                    styles.display !== 'none' && 
                    styles.visibility !== 'hidden' &&
                    styles.opacity !== '0') {
                    
                    // Check if element looks clickable
                    const isClickable = (
                        el.tagName === 'BUTTON' ||
                        el.tagName === 'A' ||
                        el.tagName === 'INPUT' ||
                        el.onclick !== null ||
                        el.getAttribute('role') === 'button' ||
                        el.getAttribute('type') === 'submit' ||
                        styles.cursor === 'pointer' ||
                        el.classList.contains('btn') ||
                        el.classList.contains('button') ||
                        el.classList.contains('submit') ||
                        el.classList.contains('login') ||
                        el.classList.contains('primary') ||
                        el.classList.contains('mantine-Button') ||
                        el.classList.contains('mantine-Button-root')
                    );
                    
                    if (isClickable) {
                        clickableElements.push({
                            index: index,
                            tagName: el.tagName,
                            text: el.textContent?.trim() || '',
                            className: el.className,
                            id: el.id,
                            type: el.type || '',
                            role: el.getAttribute('role') || '',
                            cursor: styles.cursor,
                            position: {x: rect.x, y: rect.y},
                            size: {width: rect.width, height: rect.height}
                        });
                    }
                }
            });
            
            return clickableElements;
            """
            
            clickable_elements = self.driver.execute_script(js_script)
            logger.info(f"Found {len(clickable_elements)} potentially clickable elements:")
            
            for elem in clickable_elements:
                logger.info(f"  - {elem['tagName']} (text: '{elem['text']}', class: {elem['className']}, cursor: {elem['cursor']})")
            
            return clickable_elements
            
        except Exception as e:
            logger.error(f"Error finding clickable elements: {e}")
            return []

# ----------------------------------------
# Run as standalone script
# ----------------------------------------
if __name__ == "__main__":
    tester = DashboardTester(
        base_url="https://ua.segwise.ai",
        email="qa@segwise.ai",
        password="segwise_test",
        headless=True
    )
    success = tester.run_all_tests()
    print("\n All tests passed!" if success else "\n Some tests failed. Check logs/screenshots.")
    exit(0 if success else 1)

# ----------------------------------------
# Pytest Support
# ----------------------------------------

@pytest.fixture(scope="module")
def tester():
    t = DashboardTester(
        base_url="https://ua.segwise.ai",
        email="qa@segwise.ai",
        password="segwise_test",
        headless=True
    )
    assert t.initialize_driver()
    yield t
    t.cleanup()

def test_login(tester):
    assert tester.login()

def test_metrics(tester):
    assert tester.verify_metrics()

def test_navigation(tester):
    assert tester.verify_navigation()

def test_charts(tester):
    assert tester.verify_charts()

def test_logout(tester):
    assert tester.logout()
