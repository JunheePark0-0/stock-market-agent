from crawling import get_news_html_count, get_news_html_all, get_news_content
from news_db import save_data_to_db
import sys
from selenium import webdriver
import warnings
warnings.filterwarnings('ignore')

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

tickers = {"NVDA" : 'NVIDIA', 
           "MSFT" : 'Microsoft', 
           "TSLA" : 'Tesla', 
           "LLY" : 'Eli Lilly',
           "BAC" : 'Bank of America',
           "KO" : 'Coca-Cola'}

if __name__ == "__main__":
    print("--- 뉴스 수집 시작 ---")
    if len(sys.argv) == 2:
        ticker = sys.argv[1]
        print(f"{tickers[ticker]} 종목의 뉴스를 모두 수집합니다.")
        news_texts, html_paths = get_news_html_all(ticker, chrome_options)
    else:
        ticker, count = sys.argv[1], int(sys.argv[2])
        print(f"{tickers[ticker]} 종목의 뉴스를 {count}개 수집합니다.")
        news_texts, html_paths = get_news_html_count(ticker, count, chrome_options)
    print("--- 뉴스 html 수집 완료 ---")
    print("--------------------------------")
    print("--- 뉴스 내용 수집 시작 ---")
    scraped_news = get_news_content(html_paths, chrome_options)
    print("--- 뉴스 내용 수집 완료 ---")
    print("--------------------------------")
    print("--- 뉴스 DB 저장 시작 ---")
    db_path = f"news/{ticker}.db"
    save_data_to_db(scraped_news, db_path)
    print("--- 뉴스 DB 저장 완료 ---")
    print("--------------------------------")
    print("크롤링 완료 !")