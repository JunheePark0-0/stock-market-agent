# Schema - State의 형식을 정의하는 역할

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel
import pandas as pd

class NewsArticle(BaseModel):
    """이메일 하나 스키마"""
    id : int
    title : str
    editor : str
    date : str
    content : List[Any] # str or pd.DataFrame
    html : str

