import html
import re

import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="댓글 검색",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --deep-green: #24331f;
        --forest: #355129;
        --olive: #7d8d4d;
        --olive-light: #e8ecd9;
        --orange: #e97811;
        --paper: #ffffff;
        --line: #d8ddcd;
        --gray: #666b61;
    }

    .stApp {
        background:
            radial-gradient(circle at 95% 5%, rgba(125, 141, 77, 0.12), transparent 24%),
            linear-gradient(180deg, #f7f8f2 0%, #ffffff 58%, #f1f4e8 100%);
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

    .page-hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #ffffff 0%, #edf1e2 100%);
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 1.35rem 1.55rem;
        margin-bottom: 1rem;
        box-shadow: 0 12px 30px rgba(36, 51, 31, 0.09);
    }

    .page-hero::after {
        content: "Aa  가나다  🔎";
        position: absolute;
        right: 1.5rem;
        top: 0.8rem;
        color: rgba(125, 141, 77, 0.20);
        font-size: 2.15rem;
        font-weight: 900;
        letter-spacing: 0.16rem;
    }

    .page-kicker {
        color: var(--olive);
        font-size: 0.84rem;
        font-weight: 850;
        margin-bottom: 0.2rem;
    }

    .page-title {
        margin: 0;
        color: var(--deep-green);
        font-size: 2.15rem;
        font-weight: 900;
    }

    .page-copy {
        margin: 0.4rem 0 0;
        color: var(--gray);
        font-size: 0.96rem;
    }

    .section-label {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin: 1.15rem 0 0.7rem;
        color: var(--deep-green);
        font-size: 1.15rem;
        font-weight: 850;
    }

    .section-number {
        display: inline-flex;
        width: 32px;
        height: 32px;
        align-items: center;
        justify-content: center;
        border-radius: 10px;
        background: var(--olive);
        color: white;
        font-weight: 900;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #edf1e2 100%);
        border: 1px solid #aab58d;
        border-radius: 17px;
        padding: 0.9rem 1rem;
        box-shadow: 0 8px 22px rgba(42, 58, 33, 0.08);
    }

    .comment-card {
        background: rgba(255, 255, 255, 0.97);
        border: 1px solid var(--line);
        border-left: 5px solid var(--olive);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 6px 18px rgba(36, 51, 31, 0.06);
    }

    .comment-meta {
        color: var(--olive);
        font-size: 0.82rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
    }

    .comment-text {
        color: var(--deep-green);
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .highlight {
        background: rgba(233, 120, 17, 0.24);
        color: #7b3b00;
        border-radius: 4px;
        padding: 0 0.12rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="page-hero">
        <div class="page-kicker">COMMENT SEARCH</div>
        <h1 class="page-title">검색</h1>
        <p class="page-copy">
            특정 문자열의 전체 출현 횟수와 실제 사용된 댓글을 확인합니다.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 2. 메인 페이지에서 댓글 데이터 가져오기
# ------------------------------------------------------------
def get_comments_dataframe() -> pd.DataFrame | None:
    """
    메인 페이지에서 session_state에 저장한 댓글 데이터프레임을 가져옵니다.
    """
    candidate_keys = [
        "comments_df",
        "youtube_comments_df",
        "comment_df",
    ]

    for key in candidate_keys:
        value = st.session_state.get(key)

        if isinstance(value, pd.DataFrame) and not value.empty:
            if "댓글" in value.columns:
                return value.copy()

    comments_list = st.session_state.get("comments")

    if isinstance(comments_list, list) and comments_list:
        dataframe = pd.DataFrame(comments_list)

        if "댓글" in dataframe.columns:
            return dataframe

    return None


comments_df = get_comments_dataframe()

if comments_df is None:
    st.warning(
        "검색할 댓글 데이터가 없습니다. 먼저 메인 페이지에서 댓글을 가져와 주세요."
    )
    st.info(
        '메인 페이지에서 댓글 데이터프레임을 만든 직후 '
        '`st.session_state["comments_df"] = comments_df`를 추가해야 합니다.'
    )
    st.stop()

comments_df["댓글"] = comments_df["댓글"].fillna("").astype(str)


# ------------------------------------------------------------
# 3. 검색 조건 입력
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">1</span>
        검색 조건
    </div>
    """,
    unsafe_allow_html=True,
)

search_col1, search_col2 = st.columns([2, 1])

with search_col1:
    search_text = st.text_input(
        "찾을 문자열",
        placeholder="예: 인공지능, football, ㅋㅋㅋ, 😂",
    )

with search_col2:
    case_sensitive = st.checkbox(
        "영문 대소문자 구분",
        value=False,
    )

st.caption(
    "형태소 단위가 아니라 입력한 문자열 자체를 검색합니다. "
    "따라서 단어 일부, 자모 표현, 이모지, 문장부호도 검색할 수 있습니다."
)


# ------------------------------------------------------------
# 4. 검색 함수
# ------------------------------------------------------------
def count_occurrences(text: str, query: str, case_sensitive: bool) -> int:
    """
    한 댓글 안에서 검색 문자열이 몇 번 출현하는지 계산합니다.
    """
    if not query:
        return 0

    flags = 0 if case_sensitive else re.IGNORECASE
    return len(re.findall(re.escape(query), text, flags=flags))


def highlight_text(text: str, query: str, case_sensitive: bool) -> str:
    """
    댓글에서 검색 문자열을 강조 표시합니다.
    먼저 HTML 특수문자를 이스케이프하여 화면 구조가 깨지지 않게 합니다.
    """
    safe_text = html.escape(text)
    safe_query = html.escape(query)

    flags = 0 if case_sensitive else re.IGNORECASE

    return re.sub(
        re.escape(safe_query),
        lambda match: (
            f'<span class="highlight">{match.group(0)}</span>'
        ),
        safe_text,
        flags=flags,
    )


# ------------------------------------------------------------
# 5. 검색 결과
# ------------------------------------------------------------
if search_text:
    search_text = search_text.strip()

    if search_text:
        occurrence_counts = comments_df["댓글"].apply(
            lambda text: count_occurrences(
                text,
                search_text,
                case_sensitive,
            )
        )

        matched_mask = occurrence_counts > 0
        matched_comments = comments_df.loc[matched_mask].copy()
        matched_comments["검색 문자열 출현 횟수"] = (
            occurrence_counts.loc[matched_mask].astype(int)
        )

        total_occurrences = int(
            matched_comments["검색 문자열 출현 횟수"].sum()
        )

        st.markdown(
            """
            <div class="section-label">
                <span class="section-number">2</span>
                검색 결과
            </div>
            """,
            unsafe_allow_html=True,
        )

        metric_col1, metric_col2, metric_col3 = st.columns(3)

        with metric_col1:
            st.metric(
                "검색 문자열",
                search_text,
            )

        with metric_col2:
            st.metric(
                "전체 출현 빈도",
                f"{total_occurrences:,}회",
            )

        with metric_col3:
            st.metric(
                "포함된 댓글",
                f"{len(matched_comments):,}개",
            )

        if matched_comments.empty:
            st.info("입력한 문자열이 사용된 댓글이 없습니다.")

        else:
            st.caption(
                "한 댓글에서 같은 문자열이 여러 번 나오면 모두 출현 빈도에 포함됩니다."
            )

            st.markdown(
                """
                <div class="section-label">
                    <span class="section-number">3</span>
                    문자열이 사용된 댓글
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 출현 횟수가 많은 댓글을 먼저 보여주고,
            # 같은 횟수라면 원래 수집 순서를 유지합니다.
            matched_comments = matched_comments.sort_values(
                "검색 문자열 출현 횟수",
                ascending=False,
                kind="stable",
            )

            for row_number, (_, row) in enumerate(
                matched_comments.iterrows(),
                start=1,
            ):
                author = row.get("작성자 ID", "작성자 정보 없음")
                published_at = row.get("작성 일시", "")
                likes = row.get(
                    "좋아요",
                    row.get("좋아요 수", 0),
                )
                occurrence_count = row.get(
                    "검색 문자열 출현 횟수",
                    0,
                )
                comment_text = row.get("댓글", "")

                safe_author = html.escape(str(author))
                safe_date = html.escape(str(published_at))
                highlighted_comment = highlight_text(
                    str(comment_text),
                    search_text,
                    case_sensitive,
                )

                st.markdown(
                    f"""
                    <div class="comment-card">
                        <div class="comment-meta">
                            {row_number}. {safe_author}
                            · {safe_date}
                            · 좋아요 {likes}
                            · 검색 문자열 {occurrence_count}회
                        </div>
                        <div class="comment-text">
                            {highlighted_comment}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
