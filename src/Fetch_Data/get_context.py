from src.Fetch_Data.news_fetcher import DynamoDBFetcher
from src.Fetch_Data.sec_fetcher import SEC_Fetcher
from typing import List, Tuple, Dict, Any
from pathlib import Path
import json

class GetContext:
    def __init__(self, ticker : str, keywords : List[str]):
        self.ticker = ticker
        self.keywords = keywords
        self.news_fetcher = DynamoDBFetcher()
        self.sec_fetcher = SEC_Fetcher(ticker)

    def get_context_paths(self) -> Tuple[List[Path], List[Path]]:
        new_news_paths = self.news_fetcher.fetch_news(self.ticker, self.keywords)
        new_sec_paths = self.sec_fetcher.fetch_sec_data()
        return new_news_paths, new_sec_paths

    def get_context(self) -> List[Dict]:
        new_news_paths, new_sec_paths = self.get_context_paths()
        news_context = self._process_news_context(new_news_paths)
        sec_context = self._process_sec_context(new_sec_paths)
        return news_context, sec_context

    def _process_news_context(self, paths : List[Path]) -> List[Dict]:
        context = []
        context.append("### [1] 최신 뉴스 데이터 : \n")
        for i, path in enumerate(paths, 1):
            with open(path, "r", encoding = "utf-8") as f:
                data = json.load(f)
                title = data.get("title", "N/A")
                published_at = data.get("published_at", "N/A")
                article_text = data.get("article_text", "N/A")
                context.append(
                    f"[{i}] 제목: {title}\n - 날짜: {published_at}\n - 내용: {article_text}\n")
        return context

    def _process_sec_context(self, paths : List[Path]) -> List[Dict]:
        context = []
        context.append("### [2] 최신 SEC 데이터 : \n")
        for i, path in enumerate(paths, 1):
            with open(path, "r", encoding = "utf-8") as f:
                data = json.load(f)
                context.append(data)
        return context

if __name__ == "__main__":
    # SEC DB 삭제
    db_path = Path("data/SEC/sec_filings.db")
    if db_path.exists():
        db_path.unlink()
        
    get_context = GetContext("GOOGL", ["AI", "LLM"])
    new_news_paths, new_sec_paths = get_context.get_context_paths()
    for i, path in enumerate(new_news_paths, 1):
        print(f"{i}/{len(new_news_paths)}: {path}")
    print("-"*100)
    for i, path in enumerate(new_sec_paths, 1):
        print(f"{i}/{len(new_sec_paths)}: {path}")
    print("-"*100)


    