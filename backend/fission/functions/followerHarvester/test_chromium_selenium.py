from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import subprocess

def main():
    result = {}

    # 检查 chromium 版本
    try:
        chromium_version = subprocess.check_output(["chromium-browser", "--version"])
        result["chromium"] = chromium_version.decode("utf-8").strip()
    except Exception as e:
        result["chromium_error"] = str(e)

    # 检查 chromedriver 版本
    try:
        chromedriver_version = subprocess.check_output(["chromedriver", "--version"])
        result["chromedriver"] = chromedriver_version.decode("utf-8").strip()
    except Exception as e:
        result["chromedriver_error"] = str(e)

    # 使用 selenium 启动浏览器
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://example.com")
        result["page_title"] = driver.title
        driver.quit()
    except Exception as e:
        result["selenium_error"] = str(e)

    return result
