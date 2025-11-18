from crawling import get_news_html_count, get_news_html_all, get_news_content
from news_db import save_data_to_db, compare_news_db
import sys, os
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
           "KO" : 'Coca-Cola',

           "META" : 'Meta',
           "AAPL" : "Apple",
           "GOOG" : "Google"
           }

if __name__ == "__main__":
    print("--- 뉴스 수집 시작 ---")
    if len(sys.argv) == 2:
        ticker = sys.argv[1]
        print(f"{tickers[ticker]}의 뉴스를 모두 수집합니다.")
        news_texts, html_paths = get_news_html_all(ticker, chrome_options)
    else:
        ticker, count = sys.argv[1], int(sys.argv[2])
        print(f"{tickers[ticker]}의 뉴스를 {count}개 수집합니다.")
        news_texts, html_paths = get_news_html_count(ticker, count, chrome_options)
    print("--- 뉴스 html 수집 완료 ---")
    print("--------------------------------")
    db_path = f"News/{ticker}.db"

    if os.path.exists(db_path): # 이미 존재하는 db라면, 즉 크롤링 결과가 이미 존재한다면
        print("--- html 비교 시작 ---")
        new_html_paths = [path for path in html_paths if compare_news_db(db_path, path)]
        if len(new_html_paths) == 0:
            print("새로운 뉴스가 없습니다. 크롤링을 종료합니다.")
            exit()
        print(f"새로운 뉴스 {len(new_html_paths)}개를 찾았습니다.")
        print("--- html 비교 완료 ---")
        print("--------------------------------")
        print("--- 뉴스 내용 수집 시작 ---")
        scraped_news = get_news_content(new_html_paths, chrome_options)
        print("--- 뉴스 내용 수집 완료 ---")
        print("--------------------------------")
        print("--- 뉴스 DB 저장 시작 ---")
        save_data_to_db(scraped_news, db_path)
        print("--- 뉴스 DB 저장 완료 ---")
        print("--------------------------------")
        print("크롤링 완료 !")

    else: # 새롭게 수집해오는 기업인 경우
        print("--- DB를 새롭게 생성합니다 ---")
        print("--------------------------------")
        print("--- 뉴스 내용 수집 시작 ---")
        scraped_news = get_news_content(html_paths, chrome_options)
        print("--- 뉴스 내용 수집 완료 ---")
        print("--------------------------------")
        print("--- 뉴스 DB 저장 시작 ---")
        save_data_to_db(scraped_news, db_path)
        print("--- 뉴스 DB 저장 완료 ---")
        print("--------------------------------")
        print("크롤링 완료 !")