from typing import List, Dict, Any, Optional, Literal, TypedDict
from langchain_core.tools import tool
from py_files.schemas import NewsArticle

@tool
def write_briefing(company_name : str, new_articles : List[NewsArticle]) -> str:
    """
    수집한 새로운 뉴스 기사들을 바탕으로 장 마감 브리핑 작성
    """
    pass