from typing import List
from langchain_core.tools import tool
from py_files.schemas import NewsArticle
from py_files.functions import load_prompts, format_news_articles

@tool
def write_briefing(ticker : str, new_articles : List[NewsArticle]) -> str:
    """
    수집한 새로운 뉴스 기사들을 바탕으로 장 마감 브리핑 작성
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.chat_models import init_chat_model

    tickers = {"NVDA" : 'NVIDIA', "MSFT" : 'Microsoft', "TSLA" : 'Tesla', 
               "LLY" : 'Eli Lilly', "BAC" : 'Bank of America', "KO" : 'Coca-Cola'
          }

    company_name = tickers[ticker]
    write_briefing_prompt = load_prompts("write_briefing_prompt")
    formatted_articles = format_news_articles(new_articles)

    llm = init_chat_model(model = "openai:gpt-4o-mini", temperature = 0.0)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", write_briefing_prompt["role"] + "\n" + write_briefing_prompt["instructions"]),
            ("user", write_briefing_prompt["inputs"].format(company_name = company_name, news_articles = formatted_articles))
        ]
    )
    messages = prompt.format_messages(company_name = company_name, news_articles = formatted_articles)
    response = llm.invoke(messages)

    return response.content

@tool
def save_briefing_txt(ticker : str, briefing : str) -> str:
    """
    특정 날짜의 장 마감 브리핑을 .txt 파일로 저장
    """
    import sys, os
    import datetime 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir)) # MAS_PROJECT 폴더
    save_dir = os.path.join(root_dir, "Briefings", ticker)
    os.makedirs(save_dir, exist_ok = True)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    txt_content = f"# [{today}] {ticker} 장 마감 브리핑\n\n{briefing}"
    
    with open(os.path.join(save_dir, f"{today}.txt"), "w", encoding = "utf-8") as f:
        f.write(txt_content)
    return f"장 마감 브리핑이 저장되었습니다."

@tool
def save_briefing_md(ticker : str, briefing : str) -> str:
    """
    특정 날짜의 장 마감 브리핑을 .md 파일로 저장
    """
    import sys, os
    import datetime 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir)) # MAS_PROJECT 폴더
    save_dir = os.path.join(root_dir, "Briefings", ticker)
    os.makedirs(save_dir, exist_ok = True)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    md_content = f"# [{today}] {ticker} 장 마감 브리핑\n\n{briefing}"

    with open(os.path.join(save_dir, f"{today}.md"), "w", encoding = "utf-8") as f:
        f.write(md_content)
    return f"장 마감 브리핑이 저장되었습니다."

