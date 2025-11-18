from typing import List, Dict, Any, Optional, Literal, TypedDict
from .schemas import NewsArticle

class NewsAgentState(TypedDict):
    """
    뉴스 기사 처리 State
    - 현재 분석 중인 기업
    - 새롭게 분석할 뉴스 기사들 (List[NewsArticle])
    - 최종 작성된 장 마감 브리핑 (str)
    """
    company_name : str
    new_articles : List[NewsArticle]
    final_briefing : str
