import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
import io

# Try to import selenium for JavaScript support
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Streamlit app configuration
st.set_page_config(
    page_title="Advanced Web Scraper with JS Support", 
    page_icon="🕷️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = []

# Title
st.markdown("""
<div class="main-header">
    <h1>🕷️ Advanced Web Scraper</h1>
    <p>Enhanced scraping with JavaScript support and debugging tools</p>
</div>
""", unsafe_allow_html=True)

# Check for JavaScript support
if not SELENIUM_AVAILABLE:
    st.warning("""
    ⚠️ **JavaScript Support Not Available**
    
    For JavaScript-heavy sites like ESC 365, install Selenium:
    ```
    pip install selenium
    ```
    
    You'll also need ChromeDriver for full JavaScript support.
    """)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Scraper Settings")
    
    # Scraping method
    scrape_method = st.selectbox(
        "Scraping Method:",
        ["Static HTML (Requests)", "JavaScript (Selenium)"] if SELENIUM_AVAILABLE else ["Static HTML (Requests)"],
        help="JavaScript method can handle dynamic content but is slower"
    )
    
    # Debugging options
    st.subheader("🐛 Debug Options")
    enable_debug = st.checkbox("Enable debug mode", value=True)
    show_page_source = st.checkbox("Show page source preview")
    save_html = st.checkbox("Save HTML to file")
    
    # Request settings
    st.subheader("Request Settings")
    timeout = st.slider("Timeout (seconds)", 5, 60, 20)
    delay = st.slider("Delay between requests", 1, 10, 3)
    
    if scrape_method == "JavaScript (Selenium)" and SELENIUM_AVAILABLE:
        wait_time = st.slider("Wait for content (seconds)", 5, 30, 10)
        headless = st.checkbox("Run browser in background", value=True)

def setup_selenium_driver(headless=True):
    """Setup Selenium WebDriver with proper options"""
    if not SELENIUM_AVAILABLE:
        return None
    
    try:
        options = Options()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        st.error(f"Failed to setup Chrome driver: {str(e)}")
        return None

def debug_page_content(soup, url):
    """Debug function to analyze page content"""
    debug_info = []
    
    # Basic page info
    title = soup.find('title')
    debug_info.append(f"Page Title: {title.text if title else 'No title found'}")
    
    # Find all unique classes
    all_classes = set()
    for element in soup.find_all(attrs={"class": True}):
        if isinstance(element["class"], list):
            all_classes.update(element["class"])
        else:
            all_classes.add(element["class"])
    
    debug_info.append(f"Total unique CSS classes found: {len(all_classes)}")
    
    # Look for common patterns
    cards = soup.find_all(attrs={"class": re.compile(r"card|item|result")})
    debug_info.append(f"Card-like elements found: {len(cards)}")
    
    # Check for JavaScript indicators
    scripts = soup.find_all('script')
    debug_info.append(f"Script tags found: {len(scripts)}")
    
    # Look for data attributes
    data_attrs = soup.find_all(attrs=lambda x: x and any(k.startswith('data-') for k in x.keys()) if isinstance(x, dict) else False)
    debug_info.append(f"Elements with data attributes: {len(data_attrs)}")
    
    return debug_info

def scrape_with_requests(url, columns, css_classes):
    """Traditional requests-based scraping with enhanced debugging"""
    debug_info = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        debug_info.append(f"HTTP Status: {response.status_code}")
        debug_info.append(f"Content Length: {len(response.content)} bytes")
        
        if response.status_code != 200:
            return None, [f"HTTP Error: {response.status_code}"], debug_info
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug page content
        if enable_debug:
            debug_info.extend(debug_page_content(soup, url))
        
        # Save HTML if requested
        if save_html:
            with open(f"scraped_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", 'w', encoding='utf-8') as f:
                f.write(str(soup))
            debug_info.append("HTML saved to file")
        
        # Extract data
        data = {col["name"]: [] for col in columns if col["name"]}
        errors = []
        
        for col, css_class in zip(columns, css_classes):
            if not css_class or not col["name"]:
                continue
                
            debug_info.append(f"Looking for: {col['tag']}.{css_class}")
            
            # Try multiple selector strategies
            elements = []
            
            # Strategy 1: Exact class match
            elements = soup.find_all(col["tag"], class_=css_class)
            debug_info.append(f"  Strategy 1 (exact class): {len(elements)} elements")
            
            # Strategy 2: Partial class match if no exact match
            if not elements and '.' in css_class:
                class_parts = css_class.split('.')
                for part in class_parts:
                    if part:
                        partial_elements = soup.find_all(col["tag"], class_=re.compile(part))
                        elements.extend(partial_elements)
                debug_info.append(f"  Strategy 2 (partial class): {len(elements)} elements")
            
            # Strategy 3: CSS selector
            if not elements:
                try:
                    css_selector = f"{col['tag']}.{css_class.replace('.', '.')}"
                    elements = soup.select(css_selector)
                    debug_info.append(f"  Strategy 3 (CSS selector): {len(elements)} elements")
                except Exception as e:
                    debug_info.append(f"  CSS selector failed: {str(e)}")
            
            # Extract text from found elements
            for element in elements:
                try:
                    if col.get("is_link"):
                        href = element.get('href')
                        if href:
                            full_url = urljoin(url, href)
                            data[col["name"]].append(full_url)
                        else:
                            data[col["name"]].append(None)
                    else:
                        text = element.get_text(strip=True)
                        if col.get("as_numeric"):
                            # Extract numbers
                            numbers = re.findall(r'\d+\.?\d*', text)
                            if numbers:
                                try:
                                    value = float(numbers[0]) if '.' in numbers[0] else int(numbers[0])
                                    data[col["name"]].append(value)
                                except ValueError:
                                    data[col["name"]].append(text)
                            else:
                                data[col["name"]].append(None)
                        else:
                            data[col["name"]].append(text)
                except Exception as e:
                    errors.append(f"Error extracting from {col['name']}: {str(e)}")
            
            debug_info.append(f"  Final count for {col['name']}: {len(data[col['name']])}")
        
        # Handle empty data
        if not any(data.values()) or all(len(v) == 0 for v in data.values()):
            return None, ["No data found with the specified selectors"], debug_info
        
        # Align data lengths (fix the max() error)
        max_length = 0
        for col_data in data.values():
            if len(col_data) > max_length:
                max_length = len(col_data)
        
        if max_length == 0:
            return None, ["No data extracted"], debug_info
        
        # Pad shorter columns
        for col_name in data:
            current_length = len(data[col_name])
            if current_length < max_length:
                data[col_name].extend([None] * (max_length - current_length))
        
        df = pd.DataFrame(data)
        return df, errors, debug_info
        
    except Exception as e:
        return None, [f"Critical error: {str(e)}"], debug_info

def scrape_with_selenium(url, columns, css_classes):
    """Selenium-based scraping for JavaScript content"""
    debug_info = []
    
    if not SELENIUM_AVAILABLE:
        return None, ["Selenium not available"], debug_info
    
    driver = None
    try:
        driver = setup_selenium_driver(headless)
        if not driver:
            return None, ["Failed to setup Chrome driver"], debug_info
        
        debug_info.append("Chrome driver initialized")
        
        driver.get(url)
        debug_info.append(f"Page loaded: {driver.title}")
        
        # Wait for content to load
        time.sleep(wait_time)
        
        # Get page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        debug_info.append(f"Page source length: {len(page_source)} characters")
        
        # Continue with same extraction logic as requests method
        return scrape_with_requests_logic(soup, url, columns, css_classes, debug_info)
        
    except Exception as e:
        return None, [f"Selenium error: {str(e)}"], debug_info
    finally:
        if driver:
            driver.quit()

# Main interface
st.subheader("🌐 Target Website")
url = st.text_input(
    "Enter URL:", 
    value="https://esc365.escardio.org/esc-congress/abstract?text=&docType=All&days&page=5&vue=cards",
    help="The webpage you want to scrape"
)

# Column configuration
st.subheader("📝 Data Extraction Setup")
num_columns = st.number_input("Number of columns:", min_value=1, max_value=10, value=1)

columns = []
css_classes = []

for i in range(num_columns):
    with st.expander(f"Column {i+1} - Configure", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            col_name = st.text_input(f"Column name:", value=f"Author" if i == 0 else f"Column {i+1}", key=f"name_{i}")
            css_class = st.text_input(f"CSS class:", value="search__card__header__author.font-regular" if i == 0 else "", key=f"class_{i}")
        
        with col2:
            tag_type = st.selectbox(f"HTML tag:", ["div", "span", "a", "p", "h1", "h2", "h3"], key=f"tag_{i}")
            is_link = st.checkbox(f"Extract link", key=f"link_{i}")
            as_numeric = st.checkbox(f"Convert to number", key=f"numeric_{i}")
        
        columns.append({
            "name": col_name,
            "tag": tag_type,
            "is_link": is_link,
            "as_numeric": as_numeric
        })
        css_classes.append(css_class)

# Action buttons
col_btn1, col_btn2, col_btn3 = st.columns(3)
with col_btn1:
    scrape_button = st.button("🚀 Start Scraping", type="primary")
with col_btn2:
    debug_button = st.button("🐛 Debug Page")
with col_btn3:
    clear_button = st.button("🗑️ Clear Results")
    if clear_button:
        st.session_state.scraped_data = None
        st.session_state.debug_info = []

# Debug page structure
if debug_button and url:
    with st.spinner("Analyzing page structure..."):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            st.subheader("🔍 Page Analysis")
            
            # Show page source preview
            if show_page_source:
                st.text_area("Page Source (first 2000 chars):", str(soup)[:2000], height=200)
            
            # Debug information
            debug_results = debug_page_content(soup, url)
            for info in debug_results:
                st.write(f"• {info}")
            
            # Show common classes
            all_classes = set()
            for element in soup.find_all(attrs={"class": True}):
                if isinstance(element["class"], list):
                    all_classes.update(element["class"])
                else:
                    all_classes.add(element["class"])
            
            if all_classes:
                st.subheader("🎯 Found CSS Classes")
                classes_list = sorted(list(all_classes))
                for i in range(0, len(classes_list), 3):
                    cols = st.columns(3)
                    for j, col in enumerate(cols):
                        if i + j < len(classes_list):
                            col.code(classes_list[i + j])
            else:
                st.warning("No CSS classes found - this might be a JavaScript-heavy site")
                
        except Exception as e:
            st.error(f"Debug failed: {str(e)}")

# Main scraping logic
if scrape_button and url and any(col["name"] for col in columns):
    with st.spinner("🕷️ Scraping in progress..."):
        if scrape_method == "JavaScript (Selenium)" and SELENIUM_AVAILABLE:
            df, errors, debug_info = scrape_with_selenium(url, columns, css_classes)
        else:
            df, errors, debug_info = scrape_with_requests(url, columns, css_classes)
        
        # Store debug info
        st.session_state.debug_info = debug_info
        
        # Show debug information
        if enable_debug and debug_info:
            with st.expander("🐛 Debug Information", expanded=True):
                for info in debug_info:
                    st.write(f"• {info}")
        
        # Show errors
        if errors:
            st.error("⚠️ Issues encountered:")
            for error in errors:
                st.write(f"• {error}")
        
        # Show results
        if df is not None and len(df) > 0:
            st.session_state.scraped_data = df
            st.success(f"✅ Successfully scraped {len(df)} rows!")
            
            # Display data
            st.subheader("📊 Scraped Data")
            st.dataframe(df, use_container_width=True)
            
            # Export options
            col_exp1, col_exp2 = st.columns(2)
            with col_exp1:
                csv_data = df.to_csv(index=False)
                st.download_button("📄 Download CSV", csv_data, "scraped_data.csv", "text/csv")
            with col_exp2:
                json_data = df.to_json(orient='records', indent=2)
                st.download_button("📋 Download JSON", json_data, "scraped_data.json", "application/json")
        else:
            st.error("❌ No data could be extracted. Check the debug information above.")

# Show previous results if available
if st.session_state.scraped_data is not None:
    st.subheader("📊 Current Results")
    st.dataframe(st.session_state.scraped_data, use_container_width=True)

# Help section
with st.expander("❓ Troubleshooting ESC 365"):
    st.markdown("""
    ### Common Issues with ESC 365:
    
    1. **JavaScript Required**: This site loads content dynamically
       - Use "JavaScript (Selenium)" method
       - Install: `pip install selenium`
       - Download ChromeDriver
    
    2. **CSS Class Issues**: 
       - The class `search__card__header__author.font-regular` might be:
         - Generated dynamically
         - Using CSS modules (hashed names)
         - Hidden behind user authentication
    
    3. **Alternative Approaches**:
       - Try simpler selectors like `div[class*="author"]`
       - Look for `data-` attributes
       - Check if login is required
       - Use browser developer tools to find actual selectors
    
    4. **Rate Limiting**: 
       - Add delays between requests
       - Use proper User-Agent headers
       - Respect robots.txt
    """)

st.markdown("---")
st.markdown("🕷️ **Advanced Web Scraper** | Built for JavaScript-heavy sites")
