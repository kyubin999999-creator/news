import streamlit as st
import feedparser
from newspaper import Article
from openai import OpenAI

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(page_title="뉴스 자동요약봇", layout="wide")
st.title("📰 AI 기반 자동 뉴스 요약 시스템")
st.write("인터넷에서 최신 뉴스를 자동으로 가져와 요약합니다.")

# OpenAI API 로드
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --------------------------------------------------
# 자동 수집용 한국 뉴스 RSS 목록
# --------------------------------------------------
AUTO_RSS = {
    "구글 뉴스(한국)": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "한국경제": "https://www.hankyung.com/feed",
    "머니투데이": "http://rss.mt.co.kr/mt_news.xml",
    "YTN 속보": "https://www.ytn.co.kr/rss/news.xml",
}


# --------------------------------------------------
# (1) RSS에서 자동으로 최신 기사 링크 수집
# --------------------------------------------------
def get_auto_news_links(limit=8):
    links = []
    for name, url in AUTO_RSS.items():
        feed = feedparser.parse(url)
        for e in feed.entries[:3]:    # 매체당 최대 3개
            links.append(e.link)
        if len(links) >= limit:
            break
    return links[:limit]


# --------------------------------------------------
# (2) Newspaper3k로 기사 본문 크롤링
# --------------------------------------------------
def fetch_article(url):
    article = Article(url, language="ko")
    article.download()
    article.parse()

    return {
        "title": article.title,
        "text": article.text,
        "date": article.publish_date,
        "authors": article.authors,
        "url": url,
    }


# --------------------------------------------------
# (3) OpenAI GPT 요약 생성
# --------------------------------------------------
def summarize(text):
    prompt = f"""
다음 뉴스 본문을 한국어로 핵심 요약해줘.
- 길이: 3~5문장
- 사실 중심으로 작성
- 불필요한 수식어 제거

본문:
{text}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return resp.choices[0].message["content"]


# --------------------------------------------------
# Streamlit UI 시작
# --------------------------------------------------

st.sidebar.header("설정")
news_limit = st.sidebar.slider("가져올 뉴스 개수", 3, 20, 8)

if st.button("📰 최신 뉴스 자동 가져오기 & 요약하기"):

    st.info("여러 뉴스 사이트에서 최신 기사를 자동 수집 중입니다...")
    links = get_auto_news_links(limit=news_limit)

    st.success(f"총 {len(links)}개의 뉴스를 가져왔습니다.")
    st.write("----")

    # 각 링크에 대해 처리
    for idx, url in enumerate(links):
        with st.spinner(f"{idx+1}/{len(links)} 기사 분석 중..."):
            try:
                art = fetch_article(url)
            except Exception as e:
                st.error(f"크롤링 실패: {e}")
                continue

        # 기사 제목
        st.subheader(f"{idx+1}. {art['title']}")

        # 메타 정보
        st.write(f"🗓 날짜: {art['date']}")
        st.write(f"✍ 기자: {', '.join(art['authors'])}")
        st.write(f"[🔗 원문 보기]({art['url']})")

        # 본문 미리보기
        st.write("#### 📄 본문 일부:")
        preview = art["text"][:400] + "…" if len(art["text"]) > 400 else art["text"]
        st.write(preview)

        # 요약 생성
        with st.spinner("🧠 요약 생성 중..."):
            summary = summarize(art["text"])

        st.write("### 🧠 요약")
        st.write(summary)

        st.markdown("---")

else:
    st.info("버튼을 누르면 자동으로 최신 뉴스를 가져와 요약합니다.")
