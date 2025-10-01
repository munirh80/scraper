import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

class GoogleMapsScraper:
    def __init__(self):
        """Initialize the scraper with Chrome driver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-component-extensions-with-background-pages')
        options.add_argument('--disable-component-update')
        options.add_argument('--disable-client-side-phishing-detection')
        options.add_argument('--disable-permissions-api')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--log-level=3')  # This suppresses console logs
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.results = []
    
    def search_locations(self, query, area):
        """Search for locations on Google Maps"""
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}+in+{area.replace(' ', '+')}"
        print(f"Searching: {query} in {area}")
        
        self.driver.get(search_url)
        time.sleep(5)  # Increased wait time
        
        # Wait for results to load with multiple possible selectors
        try:
            WebDriverWait(self.driver, 15).until(
                lambda driver: (
                    driver.find_elements(By.CSS_SELECTOR, '[data-result-index]') or
                    driver.find_elements(By.CSS_SELECTOR, '.hfpxzc') or
                    driver.find_elements(By.CSS_SELECTOR, '[jsaction*="click"]') or
                    driver.find_elements(By.CSS_SELECTOR, '.Nv2PK')
                )
            )
        except TimeoutException:
            print(f"No results found for {query} in {area}")
            return
        
        # Try multiple selectors for business elements
        business_elements = (
            self.driver.find_elements(By.CSS_SELECTOR, '[data-result-index]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc') or
            self.driver.find_elements(By.CSS_SELECTOR, '[jsaction*="click"]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.Nv2PK')
        )
        
        if not business_elements:
            print(f"No business elements found for {query} in {area}")
            return
            
        print(f"Found {len(business_elements)} businesses")
        
        # Scroll to load more results
        self.scroll_results()
        
        # Re-get elements after scrolling
        business_elements = (
            self.driver.find_elements(By.CSS_SELECTOR, '[data-result-index]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc') or
            self.driver.find_elements(By.CSS_SELECTOR, '[jsaction*="click"]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.Nv2PK')
        )
        
        for i in range(min(20, len(business_elements))):  # Limit to first 20 results
            try:
                # Re-find elements to avoid stale reference
                current_elements = (
                    self.driver.find_elements(By.CSS_SELECTOR, '[data-result-index]') or
                    self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc') or
                    self.driver.find_elements(By.CSS_SELECTOR, '[jsaction*="click"]') or
                    self.driver.find_elements(By.CSS_SELECTOR, '.Nv2PK')
                )
                
                if i >= len(current_elements):
                    print(f"Reached end of available elements at index {i}")
                    break
                
                current_element = current_elements[i]
                
                # Scroll element into view first
                self.driver.execute_script("arguments[0].scrollIntoView(true);", current_element)
                time.sleep(1)
                
                current_element.click()
                time.sleep(3)  # Increased wait time
                
                business_data = self.extract_business_info()
                if business_data:
                    business_data['search_query'] = query
                    business_data['search_area'] = area
                    self.results.append(business_data)
                    print(f"Extracted: {business_data.get('name', 'Unknown')}")
                
            except Exception as e:
                print(f"Error processing business {i}: {e}")
                continue
    
    def scroll_results(self):
        """Scroll through results to load more businesses"""
        try:
            # Try multiple selectors for the results panel
            results_panel = None
            selectors = ['[role="main"]', '.m6QErb', '.siAUzd', '.Nv2PK', '.search']
            
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    results_panel = elements[0]
                    break
            
            if not results_panel:
                print("Could not find results panel for scrolling")
                return
            
            for i in range(5):  # Scroll 5 times to load more results
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_panel)
                time.sleep(2)
                print(f"Scrolled {i+1}/5 times")
                
        except Exception as e:
            print(f"Error during scrolling: {e}")
            # Try alternative scrolling method
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
    
    def extract_business_info(self):
        """Extract detailed information from a business page"""
        business_data = {}
        
        try:
            # Name
            name_element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
            )
            business_data['name'] = name_element.text.strip()
            
            # Address
            try:
                address_element = self.driver.find_element(By.CSS_SELECTOR, '[data-item-id="address"] .fontBodyMedium')
                full_address = address_element.text.strip()
                business_data['full_address'] = full_address
                
                # Parse address components
                address_parts = self.parse_address(full_address)
                business_data.update(address_parts)
                
            except NoSuchElementException:
                business_data['full_address'] = 'N/A'
                business_data['street'] = 'N/A'
                business_data['postal_code'] = 'N/A'
            
            # Phone
            try:
                phone_element = self.driver.find_element(By.CSS_SELECTOR, '[data-item-id*="phone"] .fontBodyMedium')
                business_data['phone'] = phone_element.text.strip()
            except NoSuchElementException:
                business_data['phone'] = 'N/A'
            
            # Website
            try:
                website_element = self.driver.find_element(By.CSS_SELECTOR, '[data-item-id="authority"] .fontBodyMedium a')
                business_data['website'] = website_element.get_attribute('href')
            except NoSuchElementException:
                business_data['website'] = 'N/A'
            
            # Reviews
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, '.fontDisplayLarge')
                review_element = self.driver.find_element(By.CSS_SELECTOR, '.fontBodyMedium .fontBodySmall')
                
                rating = rating_element.text.strip()
                review_count = review_element.text.strip().replace('(', '').replace(')', '')
                business_data['rating'] = rating
                business_data['review_count'] = review_count
                business_data['reviews'] = f"{rating} stars ({review_count} reviews)"
                
            except NoSuchElementException:
                business_data['rating'] = 'N/A'
                business_data['review_count'] = 'N/A'
                business_data['reviews'] = 'N/A'
            
            # Photos (count)
            try:
                photo_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-photo-index]')
                business_data['photo_count'] = len(photo_elements)
            except (NoSuchElementException, TimeoutException):
                business_data['photo_count'] = 0
            
            # Location link (current URL)
            business_data['location_link'] = self.driver.current_url
            
            return business_data
            
        except Exception as e:
            print(f"Error extracting business info: {e}")
            return None
    
    def parse_address(self, address):
        """Parse address into components"""
        parts = {}
        
        # Extract postal code (5 digits at end)
        postal_match = re.search(r'\b(\d{5})\b$', address)
        if postal_match:
            parts['postal_code'] = postal_match.group(1)
            # Street is everything before the postal code and state
            street_part = re.sub(r',\s*[A-Z]{2}\s*\d{5}$', '', address)
            parts['street'] = street_part.strip()
        else:
            parts['postal_code'] = 'N/A'
            parts['street'] = address
        
        return parts
    
    def scrape_dmv_shooting_ranges(self):
        """Main method to scrape shooting ranges and gun clubs in DMV area"""
        # First, test with a simple search to see if we can access Google Maps
        print("Testing Google Maps access...")
        test_url = "https://www.google.com/maps/search/restaurants+in+Washington+DC"
        self.driver.get(test_url)
        time.sleep(5)
        
        # Check if we can find any results
        test_elements = (
            self.driver.find_elements(By.CSS_SELECTOR, '[data-result-index]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.hfpxzc') or
            self.driver.find_elements(By.CSS_SELECTOR, '[jsaction*="click"]') or
            self.driver.find_elements(By.CSS_SELECTOR, '.Nv2PK')
        )
        
        if test_elements:
            print(f"✓ Google Maps accessible - found {len(test_elements)} test results")
        else:
            print("✗ Google Maps may be blocking access or selectors need updating")
            print("Current page title:", self.driver.title)
            print("Current URL:", self.driver.current_url)
        
        queries = [
            "shooting ranges",
            "gun clubs",
            "indoor shooting ranges",
            "outdoor shooting ranges",
            "firearms training"
        ]
        
        areas = [
            "Washington DC",
            "Maryland",
            "Virginia",
            "Northern Virginia",
            "Montgomery County MD",
            "Prince George's County MD",
            "Fairfax County VA",
            "Arlington VA"
        ]
        
        for query in queries:
            for area in areas:
                try:
                    self.search_locations(query, area)
                    time.sleep(3)  # Be respectful to the server
                except Exception as e:
                    print(f"Error searching {query} in {area}: {e}")
                    continue
        
        print(f"\nTotal businesses found: {len(self.results)}")
    
    def save_to_csv(self, filename='dmv_shooting_ranges.csv'):
        """Save results to CSV file"""
        if not self.results:
            print("No data to save")
            return
        
        # Remove duplicates based on name and address
        seen = set()
        unique_results = []
        
        for result in self.results:
            identifier = (result.get('name', ''), result.get('full_address', ''))
            if identifier not in seen:
                seen.add(identifier)
                unique_results.append(result)
        
        df = pd.DataFrame(unique_results)
        
        # Reorder columns to match requirements
        column_order = [
            'name', 'website', 'phone', 'full_address', 'street', 
            'postal_code', 'reviews', 'rating', 'review_count', 
            'photo_count', 'location_link', 'search_query', 'search_area'
        ]
        
        # Ensure all columns exist
        for col in column_order:
            if col not in df.columns:
                df[col] = 'N/A'
        
        df = df[column_order]
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Data saved to {filename}")
        print(f"Unique businesses: {len(unique_results)}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()

# Main execution
if __name__ == "__main__":
    scraper = GoogleMapsScraper()
    
    try:
        print("Starting DMV Shooting Ranges Scraper...")
        print("This may take several minutes...")
        
        scraper.scrape_dmv_shooting_ranges()
        scraper.save_to_csv('dmv_shooting_ranges.csv')
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        scraper.close()
        print("Scraper finished")