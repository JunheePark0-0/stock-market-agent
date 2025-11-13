### 앞에서 crawling.py 의 결과로 
### scraped_news = scraped_news.append({'metadata' : metadata, 'content' : scraped_content}) 를 받아옴
### List[{Dict, List['str', pd.DataFrame]}]

import sqlite3
import json
import pandas as pd

create_metadata_table = """
CREATE TABLE IF NOT EXISTS Articles(
    article_id INTEGER PRIMARY KEY AUTOINCREMENT, /* 각 기사의 고유 Index */
    html TEXT UNIQUE NOT NULL, /* 기사의 HTML 주소 */
    title TEXT, /* 기사의 제목 */
    editor TEXT, /* 기사의 에디터 */
    date TEXT /* 기사의 날짜 */
    )
"""

create_content_table = """
CREATE TABLE IF NOT EXISTS Content(
    block_id INTEGER PRIMARY KEY AUTOINCREMENT, /* 각 블록의 고유 Index */
    article_id INTEGER NOT NULL, /* 기사의 고유 Index를 참조 */
    block_order INTEGER NOT NULL, /* 블록의 순서 (1부터 시작) */
    block_type TEXT NOT NULL, /* 블록의 타입 (text, table) */
    content TEXT NOT NULL, /* 블록의 내용 */
    FOREIGN KEY (article_id) REFERENCES Articles (article_id) /* 두 테이블을 연결 */
    ON DELETE CASCADE /* 기사가 삭제되면 content 블록도 삭제 */
    )
"""


def save_data_to_db(scraped_news, db_path):
    """
    스크래핑된 데이터를 받아 SQLite DB로 생성
    - metadata -> 'metadata' 테이블 생성
    - content -> 'content' 테이블 생성 
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 테이블 생성
        cursor.execute(create_metadata_table)
        cursor.execute(create_content_table)

        # 옮기기 
        for article_data in scraped_news:
            metadata = article_data['metadata']
            content = article_data['content']

            try:
                # Articles 테이블에 메타데이터 삽입
                cursor.execute(
                    """
                    INSERT INTO Articles (html, title, editor, date)
                    VALUES (?, ?, ?, ?)
                    """,
                    (metadata['html'], metadata['title'], metadata['editor'], metadata['date'])
                )

                # article_id 가져오기
                article_id = cursor.lastrowid

                # Content 테이블에 본문 삽입 
                for index, item in enumerate(content):
                    block_order = index + 1 # 1부터 시작하도록 설정

                    # 줄글 부분이면 그대로 삽입
                    if isinstance(item, str):
                        block_type = "text"
                        content_data = item
                    
                    # 데이터프레임 부분이면 json으로 바꿔서 삽입
                    elif isinstance(item, pd.DataFrame):
                        block_type = "table"
                        content_data = item.to_json(orient = "split")
                    
                    else:
                        continue
                        
                    cursor.execute(
                        """
                        INSERT INTO Content (article_id, block_order, block_type, content)
                        VALUES (?, ?, ?, ?)
                        """,
                        (article_id, block_order, block_type, content_data)
                    )
                
                print(f"DB 저장 성공 : {metadata['html']} (Article ID : {article_id})")

            # 기존에 DB 에 존재하는 기사라면
            except sqlite3.IntegrityError:
                print(f"DB 저장 건너뛰기 (이미 존재) : {metadata['html']}")
                continue
            
            except Exception as e:
                print(f"DB 저장 중 오류 발생 (기사 {metadata['html']}) : {e}")
                conn.rollback() # 이 기사에 대한 변경사항만 롤백

        conn.commit()

    except Exception as e:
        print(f"DB 연결 실패 : {e}")

    finally:
        if 'conn' in locals() and conn:
            conn.close()
            print("DB 연결 종료")