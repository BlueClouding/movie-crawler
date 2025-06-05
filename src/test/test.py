import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from lxml import html
import time
import random
import os

BASE_URL = 'https://missav.ai/ja/actresses?page='
MAX_PAGES = 1372  # Based on actual page count

def get_random_delay():
    """Return a random delay between 3 to 8 seconds"""
    return random.uniform(3, 8)

def human_like_delay():
    """Simulate human-like delay between actions"""
    time.sleep(random.uniform(0.5, 2.0))

def scroll_page(page):
    """Scroll the page randomly to simulate human behavior"""
    # Random scroll amount (25-75% of page height)
    scroll_amount = random.randint(
        int(page.viewport_size['height'] * 0.25),
        int(page.viewport_size['height'] * 0.75)
    )
    page.mouse.wheel(0, scroll_amount)
    time.sleep(random.uniform(0.5, 1.5))

def parse_html(content):
    """Parse HTML content and extract data"""
    tree = html.fromstring(content)
    items = tree.xpath('//div[contains(@class, "space-y-4")]')
    
    for item in items:
        # Extract actress name
        name_elem = item.xpath('.//h4[contains(@class, "text-nord13")]')
        name = name_elem[0].text_content().strip() if name_elem else ''
        
        # Extract number of works
        works_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "条影片")]')
        works = works_elem[0].text_content().strip('\n ') if works_elem else ''
        works = ''.join(filter(str.isdigit, works))  # Extract only digits
        
        # Extract debut year
        debut_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "出道")]')
        debut = debut_elem[0].text_content().strip('\n ') if debut_elem else ''
        debut = ''.join(filter(str.isdigit, debut))  # Extract only digits
        
        # Extract avatar URL
        avatar_elem = item.xpath('.//img')
        avatar = avatar_elem[0].get('src', '') if avatar_elem else ''
        
        # Print the results with consistent spacing
        print(f"姓名: {name.ljust(20)} 作品数: {works.ljust(4)} 出道年份: {debut.ljust(4)} 头像: {avatar}")

def setup_driver():
    # 设置Chrome选项
    options = uc.ChromeOptions()
    
    # 添加用户数据目录
    user_data_dir = os.path.join(os.path.expanduser('~'), 'chrome_profile')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    
    # 添加其他有用的参数
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument('--disable-site-isolation-trials')
    
    # 设置语言和时区
    options.add_argument('--lang=ja-JP')
    options.add_argument('--timezone=Asia/Tokyo')
    
    # 创建undetected chromedriver
    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        headless=False,
    )
    
    # 设置页面加载超时
    driver.set_page_load_timeout(60)
    
    # 设置窗口大小
    driver.set_window_size(1366, 768)
    
    return driver

def wait_for_captcha(driver):
    """等待并处理验证码"""
    try:
        # 检查是否有验证码
        captcha_found = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//*[contains(text(), "验证") or contains(text(), "Verify") or contains(text(), "CAPTCHA")]'))
        )
        if captcha_found:
            print("\n⚠️  检测到验证码，请在浏览器中完成验证...")
            input("完成后按回车键继续...")
            time.sleep(3)  # 给用户一些时间完成验证
            return True
    except TimeoutException:
        pass
    return False

def main():
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        for page_num in range(1, 3):  # 前2页
            try:
                url = f"{BASE_URL}{page_num}"
                print(f"\n正在获取第 {page_num} 页...")
                
                # 导航到页面
                driver.get(url)
                
                # 检查是否有验证码
                if wait_for_captcha(driver):
                    # 如果检测到验证码，重新加载页面
                    driver.refresh()
                
                # 等待内容加载
                try:
                    # 等待内容元素出现
                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div.space-y-4, div.grid')
                    ))
                    
                    # 模拟人类滚动
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                    time.sleep(random.uniform(1, 2))
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5);")
                    time.sleep(random.uniform(1, 2))
                    
                    # 获取页面源码
                    html_content = driver.page_source
                    
                    # 解析页面
                    parse_html(html_content)
                    
                    # 随机延迟，模拟人类浏览
                    time.sleep(random.uniform(2, 5))
                    
                except TimeoutException:
                    print(f"第 {page_num} 页内容加载超时")
                    # 保存错误页面
                    with open(f'error_page_{page_num}.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    driver.save_screenshot(f'error_page_{page_num}.png')
                    continue
                    
            except Exception as e:
                print(f"处理第 {page_num} 页时出错: {str(e)}")
                continue
                
    finally:
        # 关闭浏览器
        try:
            driver.quit()
        except:
            pass
        
        try:
            for page_num in range(1, 3):  # First 2 pages
                try:
                    url = f"{BASE_URL}{page_num}"
                    print(f"\nFetching page {page_num}...")
                    
                    # 添加随机延迟，模拟人类行为
                    time.sleep(random.uniform(1, 3))
                    
                    # 导航到页面
                    try:
                        page.goto(url, timeout=60000, wait_until='domcontentloaded')
                        # 等待页面加载完成
                        page.wait_for_load_state('networkidle', timeout=30000)
                    except Exception as e:
                        print(f"导航到页面时出错: {str(e)}")
                        continue
                    
                    # 检查是否需要验证
                    if page.locator('text=验证').count() > 0 or page.locator('iframe[src*="recaptcha"]').count() > 0:
                        print("\n⚠️  需要验证，请在浏览器中完成验证...")
                        input("完成后按回车键继续...")
                        # 等待验证完成
                        time.sleep(5)
                    
                    # 等待内容加载
                    try:
                        # 尝试等待内容加载
                        page.wait_for_selector('div.space-y-4, div.grid', timeout=10000)
                        
                        # 检查是否有内容被加载
                        if page.locator('div.space-y-4, div.grid').count() == 0:
                            print("未找到内容，可能被重定向或需要验证")
                            # 保存当前页面截图和HTML用于调试
                            page.screenshot(path=f'error_page_{page_num}.png')
                            with open(f'error_page_{page_num}.html', 'w', encoding='utf-8') as f:
                                f.write(page.content())
                            continue
                            
                    except Exception as e:
                        print(f"等待内容加载时出错: {str(e)}")
                        continue
                    
                    # 模拟人类滚动行为
                    scroll_page(page)
                    
                    # 随机延迟，模拟人类阅读时间
                    time.sleep(random.uniform(2, 5))
                    
                    # 获取页面内容
                    content = page.content()
                    
                    # 保存页面内容用于调试
                    with open(f'page_{page_num}.html', 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Parse and print the data
                    parse_html(content)
                    
                    # Random delay between pages
                    delay = get_random_delay()
                    print(f"Waiting {delay:.1f} seconds before next page...")
                    time.sleep(delay)
                    
                except Exception as e:
                    print(f"Error on page {page_num}: {str(e)}")
                    # Take a screenshot if something goes wrong
                    page.screenshot(path=f'error_page_{page_num}.png')
                    # Save the page source for debugging
                    with open(f'error_page_{page_num}.html', 'w', encoding='utf-8') as f:
                        f.write(page.content())
                    
                    # If we get blocked, we might need to close the browser and start a new session
                    if "blocked" in str(e).lower() or "captcha" in str(e).lower():
                        print("Detected blocking, restarting browser...")
                        context.close()
                        return
                    
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            
def parse_html(html_content):
    # 解析HTML内容
    tree = html.fromstring(html_content)
    
    # 查找所有演员项目
    items = tree.xpath('//div[contains(@class, "space-y-4")]//div[contains(@class, "group")]')
    
    # 如果第一个选择器没有找到项目，尝试其他选择器
    if not items:
        items = tree.xpath('//div[contains(@class, "grid")]//div[contains(@class, "group")]')
    
    for item in items:
        # 提取姓名
        name_elem = item.xpath('.//h3[contains(@class, "font-semibold")]')
        name = name_elem[0].text_content().strip('\n ') if name_elem else ''
        
        # 提取作品数量
        works_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "条影片")]')
        works = works_elem[0].text_content().strip('\n ') if works_elem else ''
        works = ''.join(filter(str.isdigit, works))  # 只提取数字
        
        # 提取出道年份
        debut_elem = item.xpath('.//p[contains(@class, "text-nord10") and contains(text(), "出道")]')
        debut = debut_elem[0].text_content().strip('\n ') if debut_elem else ''
        debut = ''.join(filter(str.isdigit, debut))  # 只提取数字
        
        # 提取头像URL
        avatar_elem = item.xpath('.//img')
        avatar = avatar_elem[0].get('src', '') if avatar_elem else ''
        
        # 打印结果，保持一致的间距
        print(f"姓名: {name.ljust(20)} 作品数: {works.ljust(4)} 出道年份: {debut.ljust(4)} 头像: {avatar}")

if __name__ == "__main__":
    main()