from typing import List, Dict, Any, Optional, Literal, TypedDict
from langchain_core.tools import tool
from py_files.schemas import NewsArticle
import os, sys, sqlite3, json, pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir)) # MAS_PROJECT 폴더
sys.path.append(root_dir)

from Crawling.crawling import get_news_html_count, get_news_content 
from Crawling.news_db import save_data_to_db, compare_news_db
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
           "KO" : 'Coca-Cola'
           }

@tool
def collect_news_articles(ticker : str, count : int) -> list:
    """
    정해진 개수의 뉴스 수집 -> 새로운 뉴스 필터링 -> 해당 뉴스들의 html 반환 NewsArticle 형식으로 변환
    """
    # print("--- 뉴스 수집 시작 ---")
    company_name = tickers[ticker]
    print(f"{company_name}의 뉴스를 {count}개 수집합니다.")
    news_texts, html_paths = get_news_html_count(ticker, count, chrome_options)
    print("--- 뉴스 html 수집 완료 ---")
    print("--------------------------------")
    db_path = f"News/{ticker}.db"

    # if os.path.exists(db_path): # 이미 존재하는 db라면, 즉 크롤링 결과가 이미 존재한다면
    #     print("--- html 비교 시작 ---")
    #     new_html_paths = [path for path in html_paths if compare_news_db(db_path, path)]
    #     if len(new_html_paths) == 0:
    #         print("새로운 뉴스가 없습니다. 크롤링을 종료합니다.")
    #         exit()

    #     print(f"새로운 뉴스 {len(new_html_paths)}개를 찾았습니다.")
    #     print("--- html 비교 완료 ---")
    #     print("--------------------------------")
    #     print("--- 뉴스 내용 수집 시작 ---")
    #     scraped_news = get_news_content(new_html_paths, chrome_options)
    #     print("--- 뉴스 내용 수집 완료 ---")
    #     print("--------------------------------")
    #     print("--- 뉴스 DB 저장 시작 ---")
    #     save_data_to_db(scraped_news, db_path)
    #     print("--- 뉴스 DB 저장 완료 ---")
    #     print("--------------------------------")
    #     print("크롤링 완료 !")
    #     return new_html_paths

    # else: # 새롭게 수집해오는 기업인 경우
    #     print("--- DB를 새롭게 생성합니다 ---")
    #     print("--------------------------------")
    #     print("--- 뉴스 내용 수집 시작 ---")
    #     scraped_news = get_news_content(html_paths, chrome_options)
    #     print("--- 뉴스 내용 수집 완료 ---")
    #     print("--------------------------------")
    #     print("--- 뉴스 DB 저장 시작 ---")
    #     save_data_to_db(scraped_news, db_path)
    #     print("--- 뉴스 DB 저장 완료 ---")
    #     print("--------------------------------")
    #     print("크롤링 완료 !")
    #     return html_paths

    scraped_news = get_news_content(html_paths, chrome_options)
    save_data_to_db(scraped_news, db_path)
    return html_paths

@tool
def convert_html_to_news_state(ticker : str, html_paths : list) -> List[NewsArticle]:
    """
    html 경로들의 기사들을 NewsArticle 형식으로 변환
    """
    if not html_paths:
        return []

    news_db_path = f"News/{ticker}.db"
    if os.path.exists(news_db_path):
        conn = sqlite3.connect(news_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # html 리스트 정돈
        html_placeholder = ",".join(["?"] * len(html_paths))

        # Articles, Content 테이블 JOIN (article_id를 기준으로)
        query = f"""
            SELECT 
                A.article_id, A.title, A.editor, A.date, A.html,
                C.content, C.block_type
            FROM Articles A
            LEFT JOIN Content C ON A.article_id = C.article_id
            WHERE A.html IN ({html_placeholder})
            ORDER BY A.article_id ASC
        """
        try:
            cursor.execute(query, html_paths)
            rows = cursor.fetchall()
            articles_map : Dict[int, dict] = {}

            for row in rows:
                article_id = row['article_id']

                if article_id not in articles_map:
                    articles_map[article_id] = {
                        "id" : article_id,
                        "title" : row['title'],
                        "editor" : row['editor'],
                        "date" : row['date'],
                        "html" : row['html'],
                        "content" : []
                    }
                
                raw_content = row["content"]
                block_type = row["block_type"]

                if raw_content:
                    if block_type == "table":
                        try:
                            table_dict = json.loads(raw_content)
                            table_df = pd.DataFrame(
                                data = table_dict.get("data", []),
                                index = table_dict.get("index", None),
                                columns = table_dict.get("columns", [])
                            )
                            articles_map[article_id]["content"].append(table_df)
                        except Exception as e:
                            print(f"테이블 변환 중 오류 발생 : {e}")
                            continue
                    else:
                        articles_map[article_id]["content"].append(str(raw_content))

            
            news_articles = []
            for article_data in articles_map.values():
                news_item = NewsArticle(**article_data)
                news_articles.append(news_item)
            return news_articles

        except Exception as e:
            print(f"HTML to NewsArticle 변환 중 오류 발생 : {e}")
            return []

        finally:
            conn.close()
        
    else:
        print(f"DB 파일이 존재하지 않습니다. : {news_db_path}")
        return []