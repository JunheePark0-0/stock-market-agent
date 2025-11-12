import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import time
import pandas as pd
from bs4 import BeautifulSoup
import requests
from itertools import repeat
from itertools import groupby

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import re
import sys

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--remote-debugging-port=9222")

def get_news_html_count(ticker, news_count):
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
                # wait.until(EC.presence_of_element_located((By.XPATH, news_path)))
                news = driver.find_element(By.XPATH, news_path)
                news_text = news.get_attribute("class") # 여기에 story-item 대신 ad-item 있으면 광고인 것

                if "ad-item" in news_text:
                    print(f"{i}번째 뉴스를 건너뜁니다. (광고)")
                else:
                    html_text = driver.find_element(By.XPATH, html_path).get_attribute("href")
                    news_texts.append(news_text)
                    html_paths.append(html_text)
                    print(f"{len(news_texts)}/{news_count} 뉴스 수집 성공 !")

                i += 1

            except Exception as e:
                print(f"뉴스 검색을 실패했습니다 : {e}")
                i += 1

    finally:
        driver.quit()

    return news_texts, html_paths

# 현재 상태의 뉴스 전부 가져오기

def get_news_html_all(ticker):
    driver = webdriver.Chrome(options = chrome_options)
    driver_url = f"https://finance.yahoo.com/quote/{ticker}/press-releases/"
    driver.get(driver_url)
    time.sleep(3)
    # wait = WebDriverWait(driver, 10)
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
                print(f"{len(news_texts)}/{len(items)} 뉴스 수집 성공 !")

            i += 1

    except Exception as e:
        print(f"뉴스 검색을 실패했습니다 : {e}")

    driver.quit()

    return news_texts, html_paths


def get_news_content(html_paths):
    try:
        driver = webdriver.Chrome(options = chrome_options)
    except Exception as e:
        print(f"WebDriver 실행 중 오류 발생 : {e}")
        return []

    wait = WebDriverWait(driver, 10)
    full_news = []

    for i, url in enumerate(html_paths, 1):
        try:        
            print(f"{i}번째 기사 처리 중")
            driver.get(url)

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
            # datetime = driver.find_element(By.XPATH, date_path).get_attribute("datetime")

            # 첫 번째 텍스트
            text_path = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[1]'
            text1 = driver.find_element(By.XPATH, text_path).text

            # 더보기 누르기
            button_path = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[2]/button'
            button = wait.until(EC.element_to_be_clickable((By.XPATH, button_path)))
            button.click()
            
            # 두 번째 텍스트
            text_path2 = '//*[@id="main-content-wrapper"]/div/article/div[4]/div/div[3]'
            text2 = wait.until(EC.visibility_of_element_located((By.XPATH, text_path2))).text
        
            full_text = text1 + "\n" + text2
            news = {'title' : title, 'editor' : editor, 'date' : date, 'text' : full_text, 'html' : url}
            full_news.append(news)

            print(f">>> {i}번째 기사 처리 완료 !")
        
        except (TimeoutException, NoSuchElementException) as e:
            print(f"{i}번째 기사에서 오류 발생 : {e}")
            continue
        except Exception as e:
            print(f"기타 오류 발생 : {e}")
            continue
        
    driver.quit()
    full_news = pd.DataFrame(full_news)
    return full_news


def save_news_content(ticker, full_news_pd):
    full_news_pd.to_csv(f"news/{ticker}_news.csv", index = False, encoding = 'utf-8-sig')
    full_news_pd.to_pickle(f"news/{ticker}_news.pickle")

if __name__ == "__main__":
    print("--- 뉴스 수집 시작 ---")
    if len(sys.argv) == 1:
        ticker = sys.argv[1]
        print(f"{ticker} 종목의 뉴스를 모두 수집합니다.")
        news_texts, html_paths = get_news_html_all(ticker)
    else:
        ticker, count = sys.argv[1], int(sys.argv[2])
        print(f"{ticker} 종목의 뉴스를 {count}개 수집합니다.")
        news_texts, html_paths = get_news_html_count(ticker, count)
    print("--- 뉴스 수집 완료 ---")

    print("--- 뉴스 내용 수집 시작 ---")
    full_news_pd = get_news_content(html_paths)
    print("--- 뉴스 내용 수집 완료 ---")

    print("--- 뉴스 저장 시작 ---")
    save_news_content(ticker, full_news_pd)

    print("크롤링 완료 !")