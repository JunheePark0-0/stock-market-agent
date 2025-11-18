import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import time
import pandas as pd
import numpy as np
import sys
from typing import List, Any, Dict

import warnings
warnings.filterwarnings('ignore')

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

def get_news_html_count(ticker, news_count, chrome_options):
    """정해진 개수만큼의 뉴스 가져오기"""
    driver = webdriver.Chrome(options = chrome_options)
    driver_url = f"https://finance.yahoo.com/quote/{ticker}/press-releases/"
    driver.get(driver_url)
    time.sleep(3)
    news_texts, html_paths = [], []
    i = 1

    try:
        wait = WebDriverWait(driver, 10)
        cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@name='agree']")))
        cookie_btn.click()
        time.sleep(2)
    except TimeoutException:
        pass

    try:
        while len(news_texts) < news_count:
            news_path = f'//*[@id="main-content-wrapper"]/section[3]/section/div/div/div/div/ul/li[{i}]'
            html_path = f'//*[@id="main-content-wrapper"]/section[3]/section/div/div/div/div/ul/li[{i}]/section/a'

            try:
                news = driver.find_element(By.XPATH, news_path)
                news_text = news.get_attribute("class") # 여기에 story-item 대신 ad-item 있으면 광고인 것

                if "ad-item" in news_text:
                    print(f"{i}번째 뉴스를 건너뜁니다. (광고)")
                else:
                    html_text = driver.find_element(By.XPATH, html_path).get_attribute("href")
                    news_texts.append(news_text)
                    html_paths.append(html_text)
                    print(f"[{len(news_texts)}/{news_count}] 뉴스 HTML 수집 성공 !")
                i += 1

            except NoSuchElementException:
                print("No HTML element found")
                i += 1

            except Exception as e:
                print(f"뉴스 검색을 실패했습니다 : {e}")
                i += 1

    finally:
        driver.quit()

    return news_texts, html_paths

def get_news_html_all(ticker, chrome_options):
    """현재 상태의 뉴스 전부 가져오기"""
    driver = webdriver.Chrome(options = chrome_options)
    driver_url = f"https://finance.yahoo.com/quote/{ticker}/press-releases/"
    driver.get(driver_url)
    time.sleep(3)
    news_texts, html_paths = [], []

    try:
        wait = WebDriverWait(driver, 10)
        cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@name='agree']")))
        cookie_btn.click()
        time.sleep(2)
    except TimeoutException:
        pass

    try:
        news_path = '//*[@id="main-content-wrapper"]/section[3]/section/div/div/div/div/ul/li'
        html_path = ".//section/a"
        items = driver.find_elements(By.XPATH, news_path)
        print(f"총 {len(items)}개의 뉴스를 찾았습니다.")

        for i, item in enumerate(items, 1):
            news_text = item.get_attribute("class")

            if "ad-item" in news_text:
                print(f"{i}번째 뉴스를 건너뜁니다. (광고)")
            else:
                html_text = item.find_element(By.XPATH, html_path).get_attribute("href")
                news_texts.append(news_text)
                html_paths.append(html_text)
                print(f"[{len(news_texts)}/{len(items)}] 뉴스 HTML 수집 성공 !")

    except NoSuchElementException:
        print("No HTML element found")
    
    except Exception as e:
        print(f"뉴스 검색을 실패했습니다 : {e}")

    driver.quit()

    return news_texts, html_paths

def _process_table(table_html):
    """테이블에서 NaN이 많은 열 제거 후 반환"""
    try:
        df = pd.read_html(table_html)[0]
        # NaN 열 제거
        no_nan_counts = df.count(axis = 0)
        df = df.loc[:, no_nan_counts > 1]
        return df

    except Exception as e:
        print(f"> 테이블 파싱 실패 : {e}")
        return None 

def _process_elements(elements, text_tags):
    """
    Selenium 요소(elements) 리스트를 받아 텍스트/테이블 분리하여 리스트로 반환
    -> 텍스트 + 테이블 리스트, 텍스트 only 문자열 반환
    """
    local_scraped_content = [] 
    local_article_content = ""

    for element in elements:
        tag = element.tag_name

        if tag in text_tags:
            text = element.text
            if text.strip():
                local_scraped_content.append(text)
                local_article_content += text + "\n"

        elif tag == "div":
            # 광고인지 확인
            class_attr = element.get_attribute("class") or ""
            testid_attr = element.get_attribute("data-testid")
            # 광고라면
            if 'yf-eondl' in class_attr or 'inarticle-ad' == testid_attr:
                # print(f"> 광고 태그 발견 - 필터링함")
                pass
            # 광고가 아닌 실제 테이블인 경우
            else:
                try:
                    table_inside = element.find_element(By.XPATH, ".//table")
                    print(f"> 내부에 테이블 존재")
                    table_html = table_inside.get_attribute("outerHTML")
                    df = _process_table(table_html)

                    if df is not None:
                        local_scraped_content.append(df)
                    
                except NoSuchElementException:
                    print(f"> 내부에 테이블 존재하지 않음 - 광고/필터링")
        
        elif tag == "figure":
            pass

        elif tag == "table":
            try:
                table_html = element.get_attribute("outerHTML")
                df = _process_table(table_html)
                if df is not None:
                    local_scraped_content.append(df)
            except Exception as e:
                print(f"> 테이블 파싱 실패 : {e}")

        else:
            print(f"> 태그 분류 실패 - {tag}")
            continue
    
    return local_scraped_content, local_article_content

def get_news_content(html_paths, chrome_options):
    """
    html에 해당하는 뉴스 내용 수집
    -> [{metadata[Dict], content[List[Any | pd.DataFrame]]}]
    """
    try:
        driver = webdriver.Chrome(options = chrome_options)
    except Exception as e:
        print(f"WebDriver 실행 중 오류 발생 : {e}")
        return []

    wait = WebDriverWait(driver, 10)
    scraped_news = []
    text_tags = ['p', 'ul', 'ol', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
    # 그 외 div : 내부에 테이블 존재 or 광고 등 / figure : 이미지

    for i, url in enumerate(html_paths, 1):
        article_content = ""
        scraped_content = []
        
        try:        
            print(f"[{i}번째 기사 처리 중]")
            driver.get(url)

            # 쿠키 팝업 처리
            try: # 있으면 클릭
                cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@name='agree']")))
                cookie_btn.click()
                time.sleep(2) # 팝업 사라질 시간
            except TimeoutException: # 팝업 없으면
                pass

            # 제목
            title_path = '//*[@id="main-content-wrapper"]/div/article/div[2]/div[2]/h1'
            title = wait.until(EC.visibility_of_element_located((By.XPATH, title_path))).text

            # 에디터 
            editor_path = '//*[@id="main-content-wrapper"]/div/article/div[3]/div[1]/div/div[1]'
            editor = driver.find_element(By.XPATH, editor_path).text

            # 날짜
            date_path = '//*[@id="main-content-wrapper"]/div/article/div[3]/div[1]/div/div[2]/time'
            date = driver.find_element(By.XPATH, date_path).text

            # 텍스트 1
            all_texts_path1 = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[1]'
            all_texts_path1 = all_texts_path1 + "/*"

            try:
                all_texts_elements1 = driver.find_elements(By.XPATH, all_texts_path1)
                print(f"Part 1: {len(all_texts_elements1)}개 요소 발견")

                scraped, article = _process_elements(all_texts_elements1, text_tags)
                scraped_content.extend(scraped)
                article_content += article

            except Exception as e:
                print(f"Part 1 스크래핑 오류 : {e}")

            # 더보기 누르기
            try:
                button_path = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[2]/button'
                button = driver.find_element(By.XPATH, button_path)
                driver.execute_script("arguments[0].click();", button)
                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[3]')))

                # 텍스트 2
                all_texts_path2 = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[3]'
                all_texts_path2 = all_texts_path2 + "/*"
                
                try:
                    all_texts_elements2 = driver.find_elements(By.XPATH, all_texts_path2)
                    print(f"Part 2: {len(all_texts_elements2)}개 요소 발견")

                    scraped, article = _process_elements(all_texts_elements2, text_tags)
                    scraped_content.extend(scraped)
                    article_content += article

                except Exception as e:
                    print(f"Part 2 스크래핑 오류 : {e}")

            except (NoSuchElementException, TimeoutException):
                print(f"더보기 버튼이 없어 Part 2를 건너뜁니다.")
                pass
            except Exception as e:
                print(f"더보기 누르기 오류 : {e}")

            # metadata, 내용 분리해서 저장
            metadata = {'title' : title, 'editor' : editor, 'date' : date, 'html' : url}
            scraped_news.append({'metadata' : metadata, 'content' : scraped_content})

            print(f">>> {i}번째 기사 처리 완료 ! ({len(scraped_content)}개 요소)")

        except Exception as e:
            print(f"오류 발생 : {e}")
            continue

    driver.quit()

    return scraped_news


def save_news_content(ticker, full_news_pd):
    full_news_pd.to_csv(f"news/{ticker}_news.csv", index = False, encoding = 'utf-8-sig')
    full_news_pd.to_pickle(f"news/{ticker}_news.pickle")

if __name__ == "__main__":
    print("--- 뉴스 수집 시작 ---")
    if len(sys.argv) == 2:
        ticker = sys.argv[1]
        print(f"{ticker} 종목의 뉴스를 모두 수집합니다.")
        news_texts, html_paths = get_news_html_all(ticker, chrome_options)
    else:
        ticker, count = sys.argv[1], int(sys.argv[2])
        print(f"{ticker} 종목의 뉴스를 {count}개 수집합니다.")
        news_texts, html_paths = get_news_html_count(ticker, count, chrome_options)
    print("--- 뉴스 수집 완료 ---")

    print("--- 뉴스 내용 수집 시작 ---")
    full_news_pd = get_news_content(html_paths, chrome_options)
    print("--- 뉴스 내용 수집 완료 ---")

    print("--- 뉴스 저장 시작 ---")
    save_news_content(ticker, full_news_pd)

    print("크롤링 완료 !")