"""
SEC EDGAR 크롤러 모듈
티커를 입력받아 SEC EDGAR에서 최신 공시 문서를 다운로드합니다.

표가 많은 공시자료의 경우 XML 형식을 권장합니다 (표 구조 보존에 최적).
XML 파일은 나중에 파싱하여 LLM에 적합한 형식(마크다운 테이블 등)으로 변환 가능합니다.
"""
from datetime import timezone, datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List

import requests, os

from src.Fetch_Data.sec_db import SEC_Database
from src.utils.time_utils import KST, get_last_24h_window, parse_iso_datetime

from dotenv import load_dotenv
load_dotenv()

class SEC_Crawler:
    """SEC EDGAR에서 기업 공시 자료를 크롤링하는 클래스"""
    
    BASE_URL = "https://www.sec.gov"
    USER_AGENT = "jhpark0256@korea.ac.kr"  # SEC 요구사항: 본인 정보로 변경 필요
    WINDOW_DAYS = int(os.getenv("SEC_CRAWLER_WINDOW_DAYS", "5"))
    
    def __init__(self, user_agent: Optional[str] = None):
        """
        Args:
            user_agent: SEC API 사용 시 필요한 User-Agent (본인/회사 정보)
        """
        self.user_agent = user_agent or self.USER_AGENT
        self.window_days = self.WINDOW_DAYS
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """
        티커로부터 CIK 번호를 조회
        Args:
            ticker: 주식 티커 심볼 (예: "NVDA")
        Returns:
            CIK 번호 (문자열) 또는 None
        """
        try:
            url = f"{self.BASE_URL}/files/company_tickers.json"
            response = self.session.get(url) # HTTP GET 요청(지정된 URL로 GET 요청)
            response.raise_for_status() # error check
            
            companies = response.json() # json으로 parsing
            
            # 티커로 CIK 찾기 (대소문자 무시)
            ticker_upper = ticker.upper()
            for entry in companies.values():
                if entry.get("ticker", "").upper() == ticker_upper:
                    cik = str(entry["cik_str"]).zfill(10)  # CIK는 10자리로 패딩
                    print(f"티커 {ticker}의 CIK: {cik}")
                    return cik
            
            print(f"티커 {ticker}에 해당하는 CIK를 찾을 수 없습니다.")
            return None
            
        except Exception as e:
            print(f"CIK 조회 중 오류 발생: {e}")
            return None

    def get_filings_in_window(self, cik: str, only_today: bool = False) -> List[Dict]:
        """
        CIK로부터 기간 내 모든 공시 정보를 조회합니다.
        Args:
            cik: CIK 번호
            only_today: True면 현재 시각 기준 직전 24시간 내 공시만 반환
        Returns:
            공시 정보 딕셔너리 리스트
        """
        try:
            # SEC EDGAR submissions JSON API 사용
            cik_padded = cik.zfill(10)  # CIK는 10자리로 패딩
            submissions_json_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
            response = self.session.get(submissions_json_url)
            response.raise_for_status()
            
            data = response.json()
            
            # submissions.json 구조 확인
            # recent : 해당 CIK의 가장 최근 제출된 공시 목록을 의미 -> 40개 내외의 최신 공시가 포함됨
            if "filings" in data and "recent" in data["filings"]:
                recent = data["filings"]["recent"]
                
                if recent and len(recent["form"]) > 0:
                    filings = []
                    if only_today:
                        if os.getenv("SEC_CRAWLER_WINDOW_DAYS"):
                            window_end = datetime.now(KST)
                            window_start = window_end - timedelta(days=self.window_days)
                        else:
                            window_start, window_end = get_last_24h_window()
                        
                        for idx in range(len(recent["form"])):
                            acceptance_dt_str = None
                            acc_kst = None
                            if recent.get("acceptanceDateTime") and len(recent["acceptanceDateTime"]) > idx:
                                acceptance_dt_str = recent["acceptanceDateTime"][idx]
                                if acceptance_dt_str:
                                    acc_dt = parse_iso_datetime(acceptance_dt_str)
                                    if acc_dt:
                                        if acc_dt.tzinfo is None:
                                            acc_dt = acc_dt.replace(tzinfo=timezone.utc)
                                        acc_kst = acc_dt.astimezone(KST)
                            filed_date = recent["filingDate"][idx]
                            candidate_dt = acc_kst or self._parse_filed_date(filed_date)
                            if not candidate_dt:
                                continue
                            if not (window_start <= candidate_dt < window_end):
                                continue
                            acceptance_date = (acc_kst or candidate_dt).date().isoformat()
                            
                            reporting_for = (
                                recent["reportDate"][idx]
                                if recent.get("reportDate")
                                and len(recent["reportDate"]) > idx
                                else None
                            )
                            filing_info = {
                                "form": recent["form"][idx],
                                "filed": filed_date,
                                "filed_date": filed_date,
                                "reporting_for": reporting_for,
                                "filing_entity": data.get("name", ""),
                                "accession_number": recent["accessionNumber"][idx],
                                "acceptance_datetime": acceptance_dt_str or filed_date,
                                "acceptance_date": acceptance_date,
                                "cik": cik
                            }
                            filings.append(filing_info)
                        
                        return filings
                    else:
                        latest_idx = 0
                        filed_date = recent["filingDate"][latest_idx]
                        reporting_for = (
                            recent["reportDate"][latest_idx]
                            if recent.get("reportDate") and len(recent["reportDate"]) > latest_idx
                            else None
                        )
                        filing_info = {
                            "form": recent["form"][latest_idx],
                            "filed": filed_date,
                            "filed_date": filed_date,
                            "reporting_for": reporting_for,
                            "filing_entity": data.get("name", ""),
                            "accession_number": recent["accessionNumber"][latest_idx],
                            "cik": cik
                        }
                        if recent.get("acceptanceDateTime") and len(recent["acceptanceDateTime"]) > latest_idx:
                            acceptance_dt_str = recent["acceptanceDateTime"][latest_idx]
                            if acceptance_dt_str:
                                acc_dt = parse_iso_datetime(acceptance_dt_str)
                                if acc_dt:
                                    if acc_dt.tzinfo is None:
                                        acc_dt = acc_dt.replace(tzinfo=timezone.utc)
                                    acc_kst = acc_dt.astimezone(KST)
                                    acceptance_date = acc_kst.date().isoformat()
                                    filing_info["acceptance_datetime"] = acceptance_dt_str
                                    filing_info["acceptance_date"] = acceptance_date
                        return [filing_info]
            
            print("해당 조건에 맞는 공시를 찾을 수 없습니다.")
            return []
            
        except Exception as e:
            print(f"공시 조회 중 오류 발생: {e}")
            return []

    def _parse_filed_date(self, filed_str: Optional[str]) -> Optional[datetime]:
        if not filed_str:
            return None
        try:
            dt = datetime.fromisoformat(filed_str)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=KST)
        else:
            dt = dt.astimezone(KST)
        return dt
    
    def get_latest_filing(self, cik: str, only_today: bool = False) -> Optional[Dict]:
        filings = self.get_filings_in_window(cik, only_today)
        return filings[0] if filings else None
    
    def download_filing_file(self, ticker: str, cik: str, accession_number: str, form: str, file_format: str = "xml") -> Optional[Path]:
        """
        공시 문서 파일을 다운로드합니다.
        """
        try:
            # 1. URL 구조에 맞게 포맷팅
            accession_no_dash = accession_number.replace("-", "")
            
            # [중요] CIK 앞의 0 제거 (예: 0001045810 -> 1045810)
            target_cik = str(int(cik)) 

            # 2. index.json 확인
            index_url = f"{self.BASE_URL}/Archives/edgar/data/{target_cik}/{accession_no_dash}/index.json"
            response = self.session.get(index_url)
            
            if response.status_code != 200:
                print(f"index.json 접속 실패 (HTTP {response.status_code}). URL: {index_url}")
                return None
                
            index_data = response.json()
            
            # 3. 파일 우선순위 설정
            file_priorities = []
            if file_format.lower() == "xml":
                file_priorities = [
                    f"{form.upper()}.xml",
                    f"{form.lower()}.xml",
                    f"{accession_no_dash}.txt"
                ]
                if "directory" in index_data:
                    for item in index_data["directory"]["item"]:
                        if item.get("name", "").endswith(".xml"):
                            file_priorities.insert(0, item["name"])
            
            elif file_format.lower() == "html":
                file_priorities = [
                    f"{form}.htm",
                    f"{form}.html",
                ]
                if "directory" in index_data:
                    for item in index_data["directory"]["item"]:
                        if item.get("name", "").endswith((".htm", ".html")):
                            file_priorities.insert(0, item["name"])
            else: 
                file_priorities = [f"{accession_no_dash}.txt"]
            
            # 4. 파일 다운로드 시도
            downloaded_file = None
            download_dir = Path("data/SEC/sec_filings")
            download_dir.mkdir(parents=True, exist_ok=True)

            for filename in file_priorities:
                try:
                    file_url = f"{self.BASE_URL}/Archives/edgar/data/{target_cik}/{accession_no_dash}/{filename}"
                    
                    file_resp = self.session.get(file_url)
                    if file_resp.status_code == 200:
                        file_path = download_dir / f"{ticker}" / f"{cik}_{accession_no_dash}_{filename}"
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(file_path, "wb") as f:
                            f.write(file_resp.content)
                        
                        print(f"파일 다운로드 완료: {file_path} ({file_format.upper()} 형식)")
                        downloaded_file = file_path
                        break
                except Exception:
                    continue
            
            if not downloaded_file:
                print(f"{file_format.upper()} 파일을 다운로드할 수 없습니다.")
                return None
            
            return downloaded_file
            
        except Exception as e:
            print(f"파일 다운로드 중 오류 발생: {e}")
            return None

    def crawl_filings_in_window(
        self,
        ticker: str,
        file_format: str = "xml",
        save_to_db: bool = True,
        db: Optional[SEC_Database] = None,
        only_today: bool = True
    ) -> List[Tuple[Dict, Path]]:
        filings: List[Tuple[Dict, Path]] = []

        cik = self.get_cik_from_ticker(ticker)
        if not cik:
            return filings

        filing_infos = self.get_filings_in_window(cik, only_today=only_today)
        if not filing_infos:
            return filings

        for filing_info in filing_infos:
            file_path = self.download_filing_file(
                ticker=ticker,
                cik=cik,
                accession_number=filing_info["accession_number"],
                form=filing_info["form"],
                file_format=file_format,
            )
            if not file_path:
                continue

            if save_to_db:
                try:
                    metadata = {
                        "ticker": ticker.upper(),
                        "acceptance_date": filing_info.get("acceptance_date"),
                        "accession_number": filing_info.get("accession_number"),
                        "cik": cik,
                        "form": filing_info.get("form"),
                        "filed_date": filing_info.get("filed_date") or filing_info.get("filed"),
                        "reporting_for": filing_info.get("reporting_for"),
                        "file_format": file_format,
                        "filing_entity": filing_info.get("filing_entity", ""),
                    }
                    database = db or SEC_Database()
                    database.save_filing(ticker, metadata, file_path)
                except Exception as e:
                    print(f"❌ 로컬 DB 저장 실패: {e}")

            filings.append((filing_info, file_path))

        return filings

    def crawl_latest_filing(
        self,
        ticker: str,
        file_format: str = "xml",
        save_to_db: bool = True,
        db: Optional[SEC_Database] = None,
        only_today: bool = True
    ) -> Optional[Tuple[Dict, Path]]:
        results = self.crawl_filings_in_window(
            ticker=ticker,
            file_format=file_format,
            save_to_db=save_to_db,
            db=db,  
            only_today=only_today,
        )
        return results[0] if results else None

def main():
    """테스트: NVIDIA의 최신 문서 다운로드"""
    crawler = SEC_Crawler()
    
    # NVIDIA 티커로 테스트
    result = crawler.crawl_filings_in_window("TSLA", only_today = False)
    
    if result:
        # metadata, file_path = result
        print("\n=== 크롤링 완료 ===")
        print(f"결과 : {len(result)}개")
        for metadata, file_path in result:
            print(f"메타데이터: {metadata}")
            print(f"파일 경로: {file_path}")
    else:
        print("크롤링 실패")

if __name__ == "__main__":
    main()