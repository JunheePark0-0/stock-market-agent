"""
SEC 공시 파일(xml)에서 필요한 부분을 파싱해오는 모듈
"""

from bs4 import BeautifulSoup
import json
from pathlib import Path

class SEC_Parser:
    def __init__(
        self, 
        ticker : str,
        xml_path : str,
        save_path : str = "data/SEC/sec_parsed"
        ):
        self.ticker = ticker
        self.xml_path = Path(xml_path)
        self.save_path = save_path

    def parse_form_144(self):
        with open(self.xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        soup = BeautifulSoup(xml_content, "lxml-xml")

        def get_text(tag_name : str):
            tag = soup.find(tag_name)
            return tag.text.strip() if tag else None
        
        try:
            shares_sold = int(get_text("noOfUnitsSold") or 0)
            market_value = float(get_text("aggregateMarketValue") or 0.0)
            outstanding = int(get_text("noOfUnitsOutstanding") or 1)
        except ValueError:
            shares_sold, market_value, outstanding = 0, 0.0, 1

        stake_sold_pct = (shares_sold / outstanding) * 100

        data = {
            # --- [기본 정보] ---
            "company": get_text("issuerName"), # 기업명
            "reporter": get_text("nameOfPersonForWhoseAccountTheSecuritiesAreToBeSold"), # 매도자 이름
            "relationship": get_text("relationshipToIssuer"), # 매도자의 직책 (관계)
            "date": get_text("approxSaleDate"), # 매도일
            
            # --- [매도 규모] ---
            "shares_sold": shares_sold, # 매도 주식 수
            "market_value": market_value, # 매도 금액
            "shares_outstanding": outstanding, # 전체 발행 주식 수
            "stake_sold_pct": round(stake_sold_pct, 6), # 매도 비중 (%)
            
            # --- [맥락 정보] ---
            "acquisition_type": get_text("natureOfAcquisitionTransaction"), # 과거 주식 취득 유형
            "acquired_date": get_text("acquiredDate"), # 과거 주식 취득 일자
            "remarks": get_text("remarks"), # 비고
            "broker": get_text("brokerOrMarketmakerDetails/name") 
        }

        file_path = self._save_to_json(data)
        return file_path
    
    def parse_form_4(self):
        with open(self.xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
        soup = BeautifulSoup(xml_content, "lxml-xml")

        def get_text(tag, child_tag=None):
            if not tag:
                return None
            target = tag
            if child_tag:
                target = tag.find(child_tag)
            if target:
                # <value> 태그가 있으면 그 안의 텍스트, 없으면 그냥 텍스트
                value_tag = target.find("value")
                return value_tag.text.strip() if value_tag else target.text.strip()
            return None

        footnotes_map = {}
        if soup.find("footnotes"):
            for fn in soup.find("footnotes").find_all("footnote"):
                fn_id = fn.get("id")
                if fn_id:
                    footnotes_map[fn_id] = fn.text.strip()

        issuer = soup.find("issuer")
        owner = soup.find("reportingOwner")
        
        data = {
            "document_type": "4",
            "period_of_report": get_text(soup, "periodOfReport"), # 보고 기준일
            "company_name": get_text(issuer, "issuerName"),
            "ticker": get_text(issuer, "issuerTradingSymbol"),
            "reporter_name": get_text(owner, "rptOwnerName"),
            "reporter_title": get_text(owner, "officerTitle"), # 직책 (예: CEO, CFO)
            "is_officer": get_text(owner, "isOfficer") == "1",
            "is_director": get_text(owner, "isDirector") == "1",
            "is_ten_percent": get_text(owner, "isTenPercentOwner") == "1",
            "transactions": [] # 거래 내역 리스트
        }

        non_derivatives = soup.find_all("nonDerivativeTransaction")
        
        for tx in non_derivatives:
                    # 각주 ID 찾기 (예: F1)
                    fn_id_tag = tx.find("footnoteId")
                    fn_text = ""
                    if fn_id_tag:
                        fn_id = fn_id_tag.get("id")
                        fn_text = footnotes_map.get(fn_id, "")

                    tx_info = {
                        "type": "Non-Derivative",
                        "security_title": get_text(tx, "securityTitle"),
                        "date": get_text(tx, "transactionDate"),
                        "code": get_text(tx.find("transactionCoding"), "transactionCode"), # G(증여), S(매도) 등
                        "action": get_text(tx.find("transactionAmounts"), "transactionAcquiredDisposedCode"), # A(취득)/D(처분)
                        "shares": float(get_text(tx.find("transactionAmounts"), "transactionShares") or 0),
                        "price": float(get_text(tx.find("transactionAmounts"), "transactionPricePerShare") or 0),
                        "shares_owned_after": float(get_text(tx.find("postTransactionAmounts"), "sharesOwnedFollowingTransaction") or 0),
                        "ownership_nature": get_text(tx.find("ownershipNature"), "directOrIndirectOwnership"), # D(직접)/I(간접)
                        "remarks": fn_text 
                    }
                    data["transactions"].append(tx_info)

        file_path = self._save_to_json(data)
        return file_path

    def _save_to_json(self, data):
        file_name = self.xml_path.name.split(".")[0]
        file_path = Path(self.save_path) / f"{self.ticker}" / f"{file_name}.json"
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding = "utf-8") as f:
            json.dump(data, f, ensure_ascii = False, indent = 4)
        return file_path


if __name__ == "__main__":
    parser = SEC_Parser("NVDA", "data/SEC/sec_filings/0001045810_000196530125000175_primary_doc.xml")
    parser.parse_xml()

