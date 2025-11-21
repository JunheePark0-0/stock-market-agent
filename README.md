# MAS_Project

[Crawling]
- 특정 기업의 뉴스 크롤링 (제목, 저자 등과 기사 본문 수집)
    - `python crawling_main.py "NVDA" 5` :  NVDA 페이지의 뉴스들을 명시한 개수만큼 수집 
    - `python crawling_main.py "NVDA"` : 현재 NVDA 페이지에 있는 모든 뉴스 수집 (대략 30개)

[Agent]
- 특정 기업의 뉴스 크롤링 & 이를 기반으로 브리핑 작성
    - `python test.py` : test.py 파일에서 기업과 뉴스 개수 설정해야 (추후 수정 예정)

[News]
- 수집된 뉴스들을 SQLite DB 형태로 저장

[Briefings]
- 뉴스를 기반으로 생성된 브리핑 대본을 txt, md 형태로 저장