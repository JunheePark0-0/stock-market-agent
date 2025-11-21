"""
Write Briefing Agent (Test)
"""
from tools.collect_news_articles import collect_news_articles, convert_html_to_news_state
from tools.write_briefing import write_briefing, save_briefing_txt, save_briefing_md

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

if __name__ == "__main__":
    print("--- Write Briefing Agent 시작 ---")
    print("--------------------------------")
    print("--- 뉴스 수집 시작 ---")
    ticker = "BAC"
    count = 5
    html_paths = collect_news_articles.invoke({"ticker" : ticker, "count" : count})
    print("--- 뉴스 수집 완료 ---")
    print("--------------------------------")
    print("--- 뉴스 상태 변환 시작 ---")
    news_state = convert_html_to_news_state.invoke({"ticker" : ticker, "html_paths" : html_paths})
    print("--- 뉴스 상태 변환 완료 ---")
    print("--------------------------------")
    print("--- 브리핑 작성 시작 ---")
    briefing = write_briefing.invoke({"ticker" : ticker, "new_articles" : news_state})
    print("--- 브리핑 작성 완료 ---")
    print("--------------------------------")
    save_briefing_txt.invoke({"ticker" : ticker, "briefing" : briefing})
    save_briefing_md.invoke({"ticker" : ticker, "briefing" : briefing})
    print("--- 브리핑 저장 완료 ---")
    print("--------------------------------")
    print(f"브리핑 : \n {briefing}")
    print("--------------------------------")
    print("--- Write Briefing Agent 완료 ---")
