"""
DynamoDB, S3에 저장된 뉴스 불러오기
- DynamoDB : kubig-YahoofinanceNews
- S3 : kubig-yahoofinancenews
"""
from __future__ import annotations

import os, json
from datetime import datetime
from zoneinfo import ZoneInfo
KST = ZoneInfo("Asia/Seoul")
from pathlib import Path
from typing import Dict, List, Optional
from functools import reduce

import boto3
from boto3.dynamodb.conditions import Attr

from bs4 import BeautifulSoup
from dotenv import load_dotenv
load_dotenv()

AWS_PROFILE = os.getenv("AWS_PROFILE")

class DynamoDBFetcher:
    def __init__(
        self, 
        table_name : str = "kubig-YahoofinanceNews",
        bucket_name : str = "kubig-yahoofinancenews",
        output_dir : str = "data/AWS",
        region_name : str = "ap-northeast-2",
        profile_name : str = AWS_PROFILE):

        self.table_name = table_name
        self.bucket_name = bucket_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents = True, exist_ok = True)

        session = boto3.Session(region_name = region_name) if region_name else boto3.Session()
        self.dynamodb = session.resource("dynamodb").Table(table_name)
        self.s3 = session.client("s3")

    def fetch_news(self, ticker : str, keywords : List[str], limit : int = 10) -> List[Dict]:
        """
        DynamoDB에서 뉴스 데이터 조회 (limit개)
        입력으로 받은 ticker에 해당하는 최신 뉴스 수집
        키워드 리스트 중 하나라고 포함하는 뉴스 수집
        S3에서 본문 내려받아 json 파일로 저장
        """
        ticker = ticker.upper()
        new_news_paths = []
        news_items_ticker = self._fetch_by_ticker(ticker)
        if not news_items_ticker:
            print(f"⚠️ 해당 ticker({ticker})의 뉴스 데이터가 없습니다.")
        
        news_items_keyword = self._fetch_by_keyword(keywords)
        if not news_items_keyword:
            print(f"⚠️ 해당 키워드({keywords})의 뉴스 데이터가 없습니다.")
        
        all_news_items = news_items_ticker + news_items_keyword
        if not all_news_items:
            print("❌ 검색된 뉴스 데이터가 없습니다.")
            return []

        # 중복 제거
        unique_news_items = {item.get("pk") : item for item in all_news_items if 'pk' in item}
        news_items = list(unique_news_items.values())

        # 최신순 정렬
        sorted_news_items = sorted(news_items, key = lambda x: x.get("et_iso", ""), reverse = True)[:limit]
        
        # saved_news = []
        for idx, item in enumerate(sorted_news_items, 1):
            article = self._download_article(item)
            if article:
                filename = self._save_article(ticker, article, idx)
                new_news_paths.append(filename)
                # saved_news.append({"filepath" : str(filename), **article})
        
        print(f"✅ {ticker} : {len(new_news_paths)}개의 뉴스 데이터 저장 완료")
        return new_news_paths
    
    def _fetch_by_ticker(self, ticker : str) -> List[Dict]:
        """
        DynamoDB에서 ticker에 해당하는 뉴스 조회
        ticker가 단순 속성이므로 query 메서드 사용 불가, scan 메서드 사용해야 함
        ticker로 필터링한 모든 뉴스 데이터 Items 반환
        """
        news_items = []
        kwargs = {
            "FilterExpression" : Attr("tickers").contains(ticker)
        }
        while True:
            response = self.dynamodb.scan(**kwargs)
            news_items.extend(response.get("Items", []))
            # 다음 페이지 시작 키 반환 -> 이 키가 보이면 아직 데이터가 남았음을 의미
            last_key = response.get("LastEvaluatedKey")
            if not last_key: # 더 이상 가져올 데이터가 없다면
                break
            # 다음에 scan할 때 여기부터 가져와야 한다고 저장해두기
            kwargs["ExclusiveStartKey"] = last_key
        
        return news_items
    
    def _fetch_by_keyword(self, keywords : List[str], limit : int = 10) -> List[Dict]:
        """
        키워드 리스트 중 하나라도 제목에 포함하고 있다면 뉴스 Items 반환
        """
        if not keywords:
            print("❌ 키워드 리스트가 비어있습니다.")
            return []
        
        news_items = []
        filter_expression = reduce(
            lambda x, y : x | y,
            [Attr("title").contains(k) for k in keywords]
        )
        kwargs = {
            "FilterExpression" : filter_expression
        }

        while True:
            response = self.dynamodb.scan(**kwargs)
            news_items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        
        return news_items

    def _download_article(self, news_item : Dict) -> Optional[Dict]:
        """
        xml 받아서 -> 본문 찾아오는 함수 
        scan 해서 조회한 뉴스에 대해 s3에서 본문 내려받아 article_raw로 저장
        xml 파일 파싱해서 내용 가져오기!
        """
        pk = news_item.get("pk")
        path = news_item.get("path") # 본문 저장하는 파일 경로
        if not pk or not path:
            print(f"❌ 뉴스 데이터 형식이 올바르지 않습니다. {news_item})")
            return None

        key = self._build_s3_key(pk, path)

        try:
            object = self.s3.get_object(Bucket = self.bucket_name, Key = key)
            raw_body = object.get("Body").read().decode("utf-8")
            clean_body = self._parse_article(raw_body)
        except Exception as e:
            print(f"❌ S3에서 뉴스 본문 다운로드 실패 : {e}")
            return None

        return {
            "pk" : pk, 
            "path" : path, # xml 파일 경로
            "tickers" : news_item.get("tickers"),
            "published_at" : news_item.get("et_iso"),
            "source" : news_item.get("source"),
            "title" : news_item.get("title"),
            "article_raw" : raw_body,
            "article_text" : clean_body
        }

    def _parse_article(self, raw_body : str) -> str:
        """
        xml 파일 파싱해서 'body' 부분만 정제, 추출
        """
        soup = BeautifulSoup(raw_body, "lxml")
        body_tag = soup.find("body")

        if body_tag:
            clean_body = body_tag.get_text(separator = "\n", strip = True)
            return clean_body
        else:
            return ""

    def _save_article(self, ticker : str, article : Dict, idx : int) -> Path:
        """
        S3에서 내려받은 본문을 json 파일로 저장
        """
        timestamp = article.get("published_at") or datetime.now(KST).isoformat()
        safe_timestamp = timestamp.replace(":", "").replace("-", "")
        filename = self.output_dir / f"{ticker}" / f"{safe_timestamp}_{idx}.json"
        Path(filename).parent.mkdir(parents = True, exist_ok = True)
        with open(filename, "w", encoding = "utf-8") as f:
            json.dump(article, f, ensure_ascii = False, indent = 2)
        return filename

    @staticmethod # 클래스 내부에 정의되어 있지만 self 없이 독립적으로 동작
    def _build_s3_key(pk : str, path : str) -> str:
        """
        DynamoDB path 값이 여러 형태일 수 있어 안전하게 S3 키 생성
        - path가 이미 .xml이라면 그대로 사용
        - path가 폴더라면 pk.xml을 붙여 저장
        """
        normalized_path = path.strip()
        if normalized_path.endswith(".xml"):
            return normalized_path
        if not normalized_path.endswith("/"):
            normalized_path = f"{normalized_path}/"
        return f"{normalized_path}{pk}.xml"

if __name__ == "__main__":
    fetcher = DynamoDBFetcher()
    results = fetcher.fetch_news("GOOGL", ["AI", "LLM"])
    for i, path in enumerate(results, 1):
        print(f"{i}/{len(results)}: {path}")