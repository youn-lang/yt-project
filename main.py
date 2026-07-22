import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pandas as pd
import requests
import streamlit as st


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="유튜브 댓글 언어 분석 도구",
    page_icon="💬",
    layout="wide",
)

# ------------------------------------------------------------
# 2. 앱 전체 디자인
# ------------------------------------------------------------
# 별도 이미지 파일 없이 HTML과 CSS만으로 화면을 꾸밉니다.
st.markdown(
    """
    <style>
    :root {
        --deep-green: #24331f;
        --forest: #355129;
        --olive: #7d8d4d;
        --olive-light: #dfe5cf;
        --orange: #e97811;
        --cream: #f7f6ef;
        --paper: #ffffff;
        --gray: #666b61;
        --line: #d8ddcd;
    }

    .stApp {
        background:
            radial-gradient(circle at 92% 8%, rgba(125, 141, 77, 0.12), transparent 24%),
            radial-gradient(circle at 10% 30%, rgba(233, 120, 17, 0.06), transparent 18%),
            linear-gradient(180deg, #f7f8f2 0%, #ffffff 55%, #f1f4e8 100%);
        color: var(--deep-green);
    }

    [data-testid="stHeader"] {
        background: rgba(247, 248, 242, 0.88);
        backdrop-filter: blur(10px);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--deep-green);
        letter-spacing: -0.03em;
    }

    .hero {
        position: relative;
        overflow: hidden;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.98), rgba(239,242,228,0.96));
        border: 1px solid var(--line);
        border-radius: 26px;
        padding: 1.45rem 1.8rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 16px 40px rgba(36, 51, 31, 0.10);
    }

    .hero::before {
        content: "";
        position: absolute;
        width: 340px;
        height: 340px;
        border-radius: 50%;
        right: -90px;
        top: -120px;
        background:
            radial-gradient(circle, rgba(125,141,77,0.23) 0%, rgba(125,141,77,0.06) 56%, transparent 72%);
    }

    .hero::after {
        content: "";
        position: absolute;
        left: -40px;
        right: -40px;
        bottom: -75px;
        height: 150px;
        background:
            radial-gradient(ellipse at 25% 20%, rgba(125,141,77,0.22), transparent 55%),
            radial-gradient(ellipse at 70% 30%, rgba(53,81,41,0.15), transparent 55%);
        transform: rotate(-2deg);
    }

    .hero-grid {
        position: relative;
        z-index: 2;
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 1.2rem;
        align-items: center;
    }

    .hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        color: var(--olive);
        font-weight: 800;
        font-size: 0.92rem;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        font-size: clamp(1.8rem, 3.1vw, 3.1rem);
        line-height: 1.06;
        font-weight: 900;
        margin: 0;
        color: var(--deep-green);
    }

    .hero-title span {
        color: var(--orange);
    }

    .hero-copy {
        margin-top: 0.65rem;
        color: var(--gray);
        font-size: 0.96rem;
        line-height: 1.55;
        max-width: 650px;
    }

    .visual-panel {
        position: relative;
        min-height: 175px;
    }

    .screen {
        position: absolute;
        right: 12px;
        top: 8px;
        width: 76%;
        height: 128px;
        border: 9px solid #2e3e28;
        border-radius: 18px;
        background: #fdfdf9;
        box-shadow: 0 16px 26px rgba(36, 51, 31, 0.18);
    }

    .screen-bar {
        height: 13px;
        border-bottom: 1px solid #d9ddcf;
        display: flex;
        gap: 6px;
        align-items: center;
        padding-left: 10px;
    }

    .screen-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #a6b17d;
    }

    .screen-content {
        display: grid;
        grid-template-columns: 48px 1fr;
        gap: 12px;
        padding: 11px;
        align-items: start;
    }

    .youtube-box {
        width: 43px;
        height: 30px;
        border-radius: 10px;
        background: var(--orange);
        position: relative;
        margin-top: 8px;
    }

    .youtube-box::after {
        content: "";
        position: absolute;
        left: 18px;
        top: 9px;
        border-left: 10px solid white;
        border-top: 6px solid transparent;
        border-bottom: 6px solid transparent;
    }

    .comment-lines {
        display: grid;
        gap: 7px;
        padding-top: 4px;
    }

    .comment-line {
        display: grid;
        grid-template-columns: 10px 1fr;
        gap: 8px;
        align-items: center;
    }

    .comment-line i {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--forest);
    }

    .comment-line b {
        display: block;
        height: 5px;
        border-radius: 999px;
        background: #bdc6aa;
    }

    .comment-line:nth-child(2) b { width: 76%; }
    .comment-line:nth-child(3) b { width: 67%; }
    .comment-line:nth-child(4) b { width: 91%; }

    .screen-stand {
        position: absolute;
        width: 68px;
        height: 13px;
        background: #2e3e28;
        right: 74px;
        top: 148px;
        border-radius: 3px;
    }

    .screen-stand::before {
        content: "";
        position: absolute;
        width: 22px;
        height: 26px;
        background: #2e3e28;
        left: 23px;
        top: -19px;
    }

    .bubble {
        position: absolute;
        background: white;
        border: 2px solid var(--olive);
        border-radius: 18px;
        box-shadow: 0 10px 20px rgba(36, 51, 31, 0.10);
    }

    .bubble.one {
        width: 76px;
        height: 50px;
        right: 0;
        top: 0;
    }

    .bubble.two {
        width: 64px;
        height: 45px;
        left: 12px;
        top: 42px;
        background: var(--olive);
        border-color: var(--olive);
    }

    .bubble::after {
        content: "";
        position: absolute;
        bottom: -12px;
        right: 18px;
        border-top: 14px solid var(--olive);
        border-left: 10px solid transparent;
        border-right: 2px solid transparent;
    }

    .bubble.two::after {
        left: 18px;
        right: auto;
    }

    .dots {
        display: flex;
        gap: 8px;
        justify-content: center;
        align-items: center;
        height: 100%;
    }

    .dots span {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--deep-green);
    }

    .bubble.two .dots span {
        background: white;
    }

    .linguistic-symbols {
        position: absolute;
        right: 70px;
        top: -4px;
        color: rgba(125, 141, 77, 0.42);
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: 0.35rem;
    }

    .section-card {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 10px 26px rgba(36, 51, 31, 0.07);
    }

    .section-heading {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        font-size: 1.12rem;
        font-weight: 850;
        color: var(--deep-green);
        margin-bottom: 0.8rem;
    }

    .section-number {
        width: 34px;
        height: 34px;
        border-radius: 10px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: var(--olive);
        color: white;
        font-weight: 900;
    }

    .small-note {
        color: #707568;
        font-size: 0.9rem;
        margin-top: 0.35rem;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #edf1e2 100%);
        border: 1px solid #aab58d;
        border-radius: 18px;
        padding: 1rem 1.2rem;
        box-shadow: 0 8px 22px rgba(42, 58, 33, 0.08);
    }

    div.stButton > button {
        border-radius: 12px;
        border: 1px solid var(--olive);
        font-weight: 750;
        min-height: 46px;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #344c25 0%, #5c742f 100%);
        border: 0;
        color: white;
    }

    div[data-testid="stDownloadButton"] button {
        border-radius: 12px;
        border: 1px solid var(--olive);
        background: #f4f6ec;
        color: var(--deep-green);
        font-weight: 750;
    }

    div[data-testid="stTextInput"] input,
    div[data-testid="stSelectbox"] > div > div {
        border-radius: 12px;
    }

    @media (max-width: 820px) {
        .hero {
            padding: 1.1rem;
        }

        .hero-grid {
            grid-template-columns: 1.15fr 0.85fr;
            gap: 0.7rem;
        }

        .visual-panel {
            min-height: 145px;
        }

        .hero-title {
            font-size: 1.8rem;
        }

        .hero-copy {
            font-size: 0.88rem;
            line-height: 1.45;
        }
    }

    @media (max-width: 520px) {
        .hero-grid {
            grid-template-columns: 1fr;
        }

        .visual-panel {
            display: none;
        }

        .hero-copy {
            margin-bottom: 0;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 3. 상단 그래픽 영역
# ------------------------------------------------------------
st.markdown(
    """
    <section class="hero">
        <div class="hero-grid">
            <div>
                <div class="hero-kicker">● YOUTUBE COMMENT LINGUISTICS</div>
                <h1 class="hero-title">
                    YouTube 댓글<br>
                    <span>언어 분석</span> 도구
                </h1>
                <p class="hero-copy">
                    유튜브 댓글을 수집하고 작성자, 시점, 표현, 반응을
                    언어학적 관점에서 분석하기 위한 데이터 수집 단계입니다.
                </p>
            </div>

            <div class="visual-panel">
                <div class="linguistic-symbols">β a あ</div>

                <div class="bubble two">
                    <div class="dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>

                <div class="screen">
                    <div class="screen-bar">
                        <span class="screen-dot"></span>
                        <span class="screen-dot"></span>
                        <span class="screen-dot"></span>
                    </div>

                    <div class="screen-content">
                        <div class="youtube-box"></div>

                        <div class="comment-lines">
                            <div class="comment-line"><i></i><b></b></div>
                            <div class="comment-line"><i></i><b></b></div>
                            <div class="comment-line"><i></i><b></b></div>
                            <div class="comment-line"><i></i><b></b></div>
                        </div>
                    </div>
                </div>

                <div class="screen-stand"></div>

                <div class="bubble one">
                    <div class="dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 4. 예시 영상 링크
# ------------------------------------------------------------
EXAMPLE_1_URL = "https://youtu.be/d95J8yzvjbQ?si=LfL5DLwCL8Pk077r"
EXAMPLE_2_URL = "https://youtu.be/I9vK5EVTt0U?si=NEZ8L7MRuNvrzINa"
EXAMPLE_3_URL = "https://www.youtube.com/watch?v=7lXj30zLaXI"

if "youtube_url" not in st.session_state:
    st.session_state.youtube_url = EXAMPLE_1_URL

st.markdown(
    """
    <div class="section-card">
        <div class="section-heading">
            <span class="section-number">1</span>
            유튜브 영상 링크 입력
        </div>
    """,
    unsafe_allow_html=True,
)

example_col1, example_col2, example_col3 = st.columns(3)

with example_col1:
    if st.button(
        "예시 1 · 딥마인드 다큐(영어 댓글)",
        use_container_width=True,
    ):
        st.session_state.youtube_url = EXAMPLE_1_URL

with example_col2:
    if st.button(
        "예시 2 · 2002 월드컵 추억(한국어 댓글)",
        use_container_width=True,
    ):
        st.session_state.youtube_url = EXAMPLE_2_URL

with example_col3:
    if st.button(
        "예시 3 · Avengers: Endgame 명장면 (일본어 댓글)",
        use_container_width=True,
    ):
        st.session_state.youtube_url = EXAMPLE_3_URL

youtube_url = st.text_input(
    "유튜브 영상 링크",
    key="youtube_url",
    placeholder="https://www.youtube.com/watch?v=영상ID",
    label_visibility="collapsed",
)

st.markdown(
    """
        <p class="small-note">
            youtu.be, youtube.com/watch, Shorts, embed, live 주소를 지원합니다.
            si 같은 부가 주소 값은 자동으로 무시합니다.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 5. 댓글 개수 선택과 실행 버튼
# ------------------------------------------------------------
control_col1, control_col2 = st.columns(2)

with control_col1:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-heading">
                <span class="section-number">2</span>
                불러올 댓글 개수
            </div>
        """,
        unsafe_allow_html=True,
    )

    comment_limit = st.selectbox(
        "불러올 댓글 개수",
        options=list(range(50, 1001, 50)),
        index=1,
        format_func=lambda number: f"{number:,}",
        help="50개부터 1,000개까지 50개 단위로 선택할 수 있습니다.",
        label_visibility="collapsed",
    )

    st.markdown(
        """
            <p class="small-note">
                50개부터 1,000개까지 50개 단위로 선택합니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with control_col2:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-heading">
                <span class="section-number">3</span>
                댓글 수집 실행
            </div>
        """,
        unsafe_allow_html=True,
    )

    load_button = st.button(
        "댓글 가져오기",
        type="primary",
        use_container_width=True,
    )

    st.markdown(
        """
            <p class="small-note">
                API에서 댓글을 수집한 뒤 좋아요가 많은 순으로 정렬합니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# 6. 유튜브 링크에서 영상 ID를 추출하는 함수
# ------------------------------------------------------------
def extract_video_id(url: str) -> str | None:
    """
    여러 형식의 유튜브 주소에서 11자리 영상 ID를 추출합니다.
    """
    if not url:
        return None

    url = url.strip()

    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    try:
        parsed = urlparse(url)

        if not parsed.netloc:
            parsed = urlparse("https://" + url)

        host = parsed.netloc.lower().split(":")[0]
        path = parsed.path.strip("/")

        if host in {"youtu.be", "www.youtu.be"}:
            candidate = path.split("/")[0]
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                return candidate

        youtube_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
        }

        if host in youtube_hosts:
            if path == "watch":
                candidate = parse_qs(parsed.query).get("v", [None])[0]
                if candidate and re.fullmatch(
                    r"[A-Za-z0-9_-]{11}",
                    candidate,
                ):
                    return candidate

            path_parts = path.split("/")
            if len(path_parts) >= 2 and path_parts[0] in {
                "shorts",
                "embed",
                "live",
            }:
                candidate = path_parts[1]
                if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
                    return candidate

    except (TypeError, ValueError):
        return None

    return None


# ------------------------------------------------------------
# 7. 작성 일시를 보기 좋은 형식으로 바꾸는 함수
# ------------------------------------------------------------
def format_published_at(value: str) -> str:
    """
    YouTube API의 ISO 날짜를 '연-월-일 시:분' 형식으로 바꿉니다.
    """
    if not value:
        return ""

    try:
        parsed_date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed_date.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


# ------------------------------------------------------------
# 8. YouTube Data API에서 댓글을 여러 페이지 가져오는 함수
# ------------------------------------------------------------
def fetch_youtube_comments(
    video_id: str,
    api_key: str,
    requested_count: int,
) -> list[dict]:
    """
    commentThreads API는 한 번에 최대 100개까지만 반환합니다.
    nextPageToken을 사용해 여러 번 요청하여 최대 1,000개까지 수집합니다.
    """
    api_url = "https://www.googleapis.com/youtube/v3/commentThreads"

    comments = []
    next_page_token = None

    while len(comments) < requested_count:
        remaining_count = requested_count - len(comments)

        params = {
            "part": "snippet",
            "videoId": video_id,
            "key": api_key,
            "maxResults": min(100, remaining_count),
            "order": "relevance",
            "textFormat": "plainText",
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        response = requests.get(
            api_url,
            params=params,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()

        for item in data.get("items", []):
            snippet = (
                item.get("snippet", {})
                .get("topLevelComment", {})
                .get("snippet", {})
            )

            # 화면에 표시되는 작성자명을 우선 사용합니다.
            # 이름이 없는 경우 채널 ID를 대신 사용합니다.
            author_channel = snippet.get("authorChannelId", {})
            author_id = (
                snippet.get("authorDisplayName")
                or author_channel.get("value")
                or "알 수 없음"
            )

            comments.append(
                {
                    "작성자 ID": author_id,
                    "작성 일시": format_published_at(
                        snippet.get("publishedAt", "")
                    ),
                    "댓글": snippet.get("textOriginal", ""),
                    "좋아요": int(snippet.get("likeCount", 0)),
                }
            )

            if len(comments) >= requested_count:
                break

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    comments.sort(
        key=lambda item: item["좋아요"],
        reverse=True,
    )

    return comments[:requested_count]


# ------------------------------------------------------------
# 9. CSV 다운로드용 데이터를 만드는 함수
# ------------------------------------------------------------
def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    """
    엑셀에서 한글이 깨지지 않도록 UTF-8 BOM 형식으로 저장합니다.
    """
    return df.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")


# ------------------------------------------------------------
# 10. 댓글 불러오기
# ------------------------------------------------------------
if load_button:
    video_id = extract_video_id(youtube_url)

    if not video_id:
        st.error(
            "유튜브 영상 ID를 찾지 못했습니다. "
            "youtu.be 또는 youtube.com/watch 형식의 링크인지 확인해 주세요."
        )
        st.stop()

    try:
        youtube_api_key = st.secrets["YOUTUBE_API_KEY"]
    except KeyError:
        st.error(
            "YouTube API 키가 설정되지 않았습니다. "
            "Streamlit Cloud의 Secrets에 "
            '`YOUTUBE_API_KEY = "발급받은_API_키"` 형식으로 등록해 주세요.'
        )
        st.stop()

    progress_message = (
        f"댓글을 최대 {comment_limit:,}개까지 불러오는 중입니다. "
        "선택한 개수가 많으면 API를 여러 번 호출합니다."
    )

    with st.spinner(progress_message):
        try:
            comments = fetch_youtube_comments(
                video_id=video_id,
                api_key=youtube_api_key,
                requested_count=comment_limit,
            )

            if not comments:
                st.warning(
                    "가져올 수 있는 댓글이 없습니다. "
                    "댓글이 없거나 댓글 작성이 제한된 영상일 수 있습니다."
                )
                st.stop()

            comments_df = pd.DataFrame(
                comments,
                columns=["작성자 ID", "작성 일시", "댓글", "좋아요"],
            )

            # 서브 페이지에서 사용할 데이터 저장
            st.session_state["comments_df"] = comments_df
            st.session_state["video_id"] = video_id
            st.session_state["video_url"] = youtube_url

            metric_col1, metric_col2 = st.columns(2)

            with metric_col1:
                st.metric(
                    "가져온 댓글 수",
                    f"{len(comments_df):,}개",
                )

            with metric_col2:
                st.metric(
                    "댓글 좋아요 합계",
                    f"{comments_df['좋아요'].sum():,}개",
                )

            st.markdown(
                """
                <div class="section-card">
                    <div class="section-heading">
                        <span class="section-number">4</span>
                        댓글 목록
                    </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption("전체 수집 결과를 좋아요가 많은 순으로 정렬했습니다.")

            csv_data = dataframe_to_csv(comments_df)

            st.download_button(
                label="CSV 파일 다운로드",
                data=csv_data,
                file_name=f"youtube_comments_{video_id}.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.dataframe(
                comments_df,
                use_container_width=True,
                hide_index=True,
                height=600,
                column_config={
                    "작성자 ID": st.column_config.TextColumn(
                        "작성자 ID",
                        width="medium",
                    ),
                    "작성 일시": st.column_config.TextColumn(
                        "작성 일시",
                        width="medium",
                    ),
                    "댓글": st.column_config.TextColumn(
                        "댓글",
                        width="large",
                    ),
                    "좋아요": st.column_config.NumberColumn(
                        "좋아요",
                        format="%d",
                        width="small",
                    ),
                },
            )

            st.markdown("</div>", unsafe_allow_html=True)

            if len(comments_df) < comment_limit:
                st.info(
                    f"최대 {comment_limit:,}개를 요청했지만 "
                    f"이 영상에서 가져올 수 있는 공개 댓글은 "
                    f"{len(comments_df):,}개였습니다."
                )

        except requests.exceptions.Timeout:
            st.error(
                "YouTube 서버의 응답이 지연되고 있습니다. "
                "잠시 후 다시 시도해 주세요."
            )

        except requests.exceptions.HTTPError as error:
            status_code = error.response.status_code

            try:
                error_data = error.response.json()
                api_message = (
                    error_data.get("error", {})
                    .get("message", "")
                )
            except ValueError:
                api_message = ""

            if status_code == 403:
                st.error(
                    "댓글을 가져오지 못했습니다. "
                    "댓글이 비활성화된 영상이거나, API 키 권한 또는 "
                    "일일 API 할당량에 문제가 있을 수 있습니다."
                )
            elif status_code == 404:
                st.error(
                    "영상을 찾지 못했습니다. "
                    "삭제되었거나 비공개 영상인지 확인해 주세요."
                )
            elif status_code == 400:
                st.error(
                    "요청한 영상 정보를 처리할 수 없습니다. "
                    "유튜브 링크가 올바른지 확인해 주세요."
                )
            else:
                message = (
                    "댓글을 가져오는 중 YouTube API 오류가 발생했습니다. "
                    f"HTTP 상태 코드: {status_code}"
                )
                if api_message:
                    message += f" / API 메시지: {api_message}"
                st.error(message)

        except requests.exceptions.RequestException:
            st.error(
                "네트워크 문제로 댓글을 가져오지 못했습니다. "
                "인터넷 연결 상태를 확인한 뒤 다시 시도해 주세요."
            )

        except Exception as error:
            st.error(
                "예상하지 못한 오류가 발생했습니다. "
                "링크와 API 키 설정을 확인해 주세요."
            )
            st.exception(error)
