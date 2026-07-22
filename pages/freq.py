import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st
from kiwipiepy import Kiwi


# ------------------------------------------------------------
# 1. 페이지 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="어휘 분석",
    page_icon="🔤",
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
        content: "Aa  가나다  #  💬";
        position: absolute;
        right: 1.5rem;
        top: 0.8rem;
        color: rgba(125, 141, 77, 0.20);
        font-size: 2.25rem;
        font-weight: 900;
        letter-spacing: 0.18rem;
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

    div.stButton > button,
    div[data-testid="stDownloadButton"] button {
        border-radius: 12px;
        border: 1px solid var(--olive);
        font-weight: 750;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #344c25 0%, #5c742f 100%);
        border: 0;
        color: white;
    }

    .comment-card {
        background: rgba(255,255,255,0.95);
        border-left: 5px solid var(--olive);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 5px 16px rgba(36, 51, 31, 0.06);
    }

    .comment-meta {
        color: var(--olive);
        font-size: 0.82rem;
        font-weight: 800;
        margin-bottom: 0.25rem;
    }

    .comment-text {
        color: var(--deep-green);
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="page-hero">
        <div class="page-kicker">LEXICAL ANALYSIS</div>
        <h1 class="page-title">어휘 분석</h1>
        <p class="page-copy">
            수집한 댓글을 형태소 단위로 분석하고 빈도와 실제 사용 문맥을 확인합니다.
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
    메인 페이지에서 저장한 댓글 데이터프레임을 가져옵니다.

    권장 저장 키:
    st.session_state["comments_df"] = comments_df
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

    # 리스트 형태로 저장된 경우도 처리합니다.
    comments_list = st.session_state.get("comments")

    if isinstance(comments_list, list) and comments_list:
        dataframe = pd.DataFrame(comments_list)
        if "댓글" in dataframe.columns:
            return dataframe

    return None


comments_df = get_comments_dataframe()

if comments_df is None:
    st.warning(
        "분석할 댓글 데이터가 없습니다. 먼저 메인 페이지에서 댓글을 가져와 주세요."
    )
    st.info(
        '메인 페이지에서 댓글 데이터프레임을 만든 직후 '
        '`st.session_state["comments_df"] = comments_df`를 추가해야 합니다.'
    )
    st.stop()

comments_df["댓글"] = comments_df["댓글"].fillna("").astype(str)

metric_col1, metric_col2 = st.columns(2)

with metric_col1:
    st.metric("분석 대상 댓글", f"{len(comments_df):,}개")

with metric_col2:
    non_empty_count = comments_df["댓글"].str.strip().ne("").sum()
    st.metric("내용이 있는 댓글", f"{non_empty_count:,}개")


# ------------------------------------------------------------
# 3. 형태소 분석 준비
# ------------------------------------------------------------
@st.cache_resource
def load_kiwi() -> Kiwi:
    """
    Kiwi 분석기는 처음 한 번만 불러오고 이후에는 재사용합니다.
    """
    return Kiwi()


# Kiwi 품사 태그를 초보자가 읽기 쉬운 한국어 명칭으로 바꿉니다.
POS_NAMES = {
    "NNG": "일반 명사",
    "NNP": "고유 명사",
    "NNB": "의존 명사",
    "NR": "수사",
    "NP": "대명사",
    "VV": "동사",
    "VA": "형용사",
    "VX": "보조 용언",
    "VCP": "긍정 지정사",
    "VCN": "부정 지정사",
    "MM": "관형사",
    "MAG": "일반 부사",
    "MAJ": "접속 부사",
    "IC": "감탄사",
    "JKS": "주격 조사",
    "JKC": "보격 조사",
    "JKG": "관형격 조사",
    "JKO": "목적격 조사",
    "JKB": "부사격 조사",
    "JKV": "호격 조사",
    "JKQ": "인용격 조사",
    "JX": "보조사",
    "JC": "접속 조사",
    "EP": "선어말 어미",
    "EF": "종결 어미",
    "EC": "연결 어미",
    "ETN": "명사형 전성 어미",
    "ETM": "관형형 전성 어미",
    "XPN": "접두사",
    "XSN": "명사 파생 접미사",
    "XSV": "동사 파생 접미사",
    "XSA": "형용사 파생 접미사",
    "XR": "어근",
    "SF": "마침표·물음표·느낌표",
    "SP": "쉼표·가운뎃점·콜론",
    "SS": "괄호·따옴표",
    "SSO": "여는 괄호·따옴표",
    "SSC": "닫는 괄호·따옴표",
    "SE": "줄임표",
    "SO": "붙임표",
    "SW": "기타 기호",
    "SL": "영문",
    "SH": "한자",
    "SN": "숫자",
    "W_URL": "URL",
    "W_EMAIL": "이메일",
    "W_HASHTAG": "해시태그",
    "W_MENTION": "멘션",
    "W_SERIAL": "일련번호",
    "Z_CODA": "덧붙은 받침",
    "USER0": "사용자 정의어",
}


# 유니코드의 대표적인 이모지 범위를 검사합니다.
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]"
)

# 이모지 조합에 붙는 변형 선택자와 피부색 문자를 함께 처리합니다.
EMOJI_SEQUENCE_PATTERN = re.compile(
    r"(?:"
    + EMOJI_PATTERN.pattern
    + r")(?:[\uFE0F\u200D\U0001F3FB-\U0001F3FF]*"
    + EMOJI_PATTERN.pattern
    + r")*"
)


def make_base_form(form: str, tag: str) -> str:
    """
    Kiwi가 분리한 용언 어간에는 사전형 어미 '다'를 붙입니다.
    영어는 소문자로 통일하고, 나머지는 분석된 형태를 유지합니다.
    """
    if tag.startswith(("VV", "VA", "VX", "VCP", "VCN")):
        return f"{form}다"

    if tag == "SL":
        return form.lower()

    return form


def analyze_comments(comment_series: pd.Series) -> pd.DataFrame:
    """
    모든 댓글을 분석하여 단어별 빈도수·품사·기본형을 집계합니다.
    """
    kiwi = load_kiwi()
    rows = []

    for text in comment_series:
        text = str(text)

        # Kiwi가 반환하는 형태소를 기록합니다.
        for token in kiwi.tokenize(text):
            form = token.form.strip()
            tag = token.tag

            if not form:
                continue

            # 기호로 분석된 토큰 안에 이모지가 있으면 이모지로 분류합니다.
            emoji_items = EMOJI_SEQUENCE_PATTERN.findall(form)

            if emoji_items:
                for emoji_text in emoji_items:
                    rows.append(
                        {
                            "단어": emoji_text,
                            "품사": "이모지",
                            "기본형": emoji_text,
                        }
                    )

                # 토큰 전체가 이모지인 경우 일반 기호 행은 추가하지 않습니다.
                remaining = EMOJI_SEQUENCE_PATTERN.sub("", form).strip()
                if not remaining:
                    continue

            # 영어는 대소문자 차이를 같은 단어로 집계합니다.
            display_form = form.lower() if tag == "SL" else form

            rows.append(
                {
                    "단어": display_form,
                    "품사": POS_NAMES.get(tag, tag),
                    "기본형": make_base_form(form, tag),
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=["단어", "빈도수", "품사", "기본형"]
        )

    token_df = pd.DataFrame(rows)

    result_df = (
        token_df.groupby(
            ["단어", "품사", "기본형"],
            as_index=False,
            dropna=False,
        )
        .size()
        .rename(columns={"size": "빈도수"})
        .sort_values(
            ["빈도수", "단어"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    return result_df[["단어", "빈도수", "품사", "기본형"]]


@st.cache_data(show_spinner=False)
def cached_analyze_comments(comment_tuple: tuple[str, ...]) -> pd.DataFrame:
    """
    같은 댓글을 다시 분석할 때 결과를 재사용합니다.
    """
    return analyze_comments(pd.Series(comment_tuple))


with st.spinner("댓글 전체를 형태소 분석하는 중입니다..."):
    lexical_df = cached_analyze_comments(
        tuple(comments_df["댓글"].tolist())
    )


# ------------------------------------------------------------
# 4. 형태소 분석 결과와 CSV 다운로드
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">1</span>
        형태소 분석 결과
    </div>
    """,
    unsafe_allow_html=True,
)

if lexical_df.empty:
    st.warning("형태소 분석 결과가 없습니다.")
    st.stop()

result_col1, result_col2 = st.columns([1, 1])

with result_col1:
    st.metric("서로 다른 분석 항목", f"{len(lexical_df):,}개")

with result_col2:
    st.metric("전체 형태소 수", f"{lexical_df['빈도수'].sum():,}개")

csv_data = lexical_df.to_csv(
    index=False,
    encoding="utf-8-sig",
).encode("utf-8-sig")

st.download_button(
    "형태소 분석 결과 CSV 다운로드",
    data=csv_data,
    file_name="youtube_comment_lexical_analysis.csv",
    mime="text/csv",
    use_container_width=True,
)

with st.expander("형태소 분석 표 보기", expanded=False):
    st.dataframe(
        lexical_df,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={
            "단어": st.column_config.TextColumn("단어", width="medium"),
            "빈도수": st.column_config.NumberColumn(
                "빈도수",
                format="%d",
                width="small",
            ),
            "품사": st.column_config.TextColumn("품사", width="medium"),
            "기본형": st.column_config.TextColumn("기본형", width="medium"),
        },
    )


# ------------------------------------------------------------
# 5. 출현 빈도 분석
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">2</span>
        출현 빈도 분석
    </div>
    """,
    unsafe_allow_html=True,
)

frequency_col1, frequency_col2 = st.columns([1, 2])

with frequency_col1:
    top_n = st.number_input(
        "표시할 상위 단어 수",
        min_value=5,
        max_value=min(200, max(5, len(lexical_df))),
        value=min(20, max(5, len(lexical_df))),
        step=5,
    )

    remove_symbols = st.checkbox(
        "문장부호와 기타 기호 제외",
        value=True,
    )

with frequency_col2:
    st.caption(
        "영문으로 분석된 알파벳 한 글자 단어는 자동으로 제외합니다."
    )


frequency_df = lexical_df.copy()

# 영어 한 글자 단어를 제외합니다.
one_letter_english = (
    frequency_df["단어"].str.fullmatch(r"[A-Za-z]", na=False)
)
frequency_df = frequency_df[~one_letter_english]

if remove_symbols:
    excluded_pos = {
        "마침표·물음표·느낌표",
        "쉼표·가운뎃점·콜론",
        "괄호·따옴표",
        "여는 괄호·따옴표",
        "닫는 괄호·따옴표",
        "줄임표",
        "붙임표",
        "기타 기호",
    }
    frequency_df = frequency_df[
        ~frequency_df["품사"].isin(excluded_pos)
    ]

# 같은 기본형과 품사를 하나로 합쳐 실제 어휘 빈도를 계산합니다.
frequency_df = (
    frequency_df.groupby(
        ["기본형", "품사"],
        as_index=False,
    )["빈도수"]
    .sum()
    .sort_values(
        ["빈도수", "기본형"],
        ascending=[False, True],
    )
    .head(int(top_n))
    .rename(columns={"기본형": "단어"})
)

if frequency_df.empty:
    st.warning("현재 조건에 표시할 단어가 없습니다.")
else:
    list_col, chart_col = st.columns([0.8, 1.7])

    with list_col:
        st.dataframe(
            frequency_df[["단어", "빈도수", "품사"]],
            use_container_width=True,
            hide_index=True,
            height=max(300, min(680, 42 * len(frequency_df) + 38)),
        )

    with chart_col:
        # 그래프에서 빈도가 큰 단어가 위에 오도록 역순으로 전달합니다.
        chart_df = frequency_df.iloc[::-1].copy()

        figure = px.bar(
            chart_df,
            x="빈도수",
            y="단어",
            orientation="h",
            text="빈도수",
            hover_data={"품사": True},
        )

        figure.update_traces(
            marker_color="#7d8d4d",
            textposition="outside",
            cliponaxis=False,
        )

        figure.update_layout(
            height=max(430, 31 * len(chart_df)),
            margin=dict(l=10, r=45, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="출현 빈도수",
            yaxis_title="",
            font=dict(color="#24331f"),
        )

        figure.update_xaxes(
            showgrid=True,
            gridcolor="rgba(125,141,77,0.16)",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
            config={"displayModeBar": False},
        )


# ------------------------------------------------------------
# 6. 문자열 검색
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">3</span>
        문자열 검색
    </div>
    """,
    unsafe_allow_html=True,
)

search_text = st.text_input(
    "찾을 문자열",
    placeholder="예: 인공지능, football, 😂",
)

case_sensitive = st.checkbox(
    "영문 대소문자 구분",
    value=False,
)

if search_text:
    search_text = search_text.strip()

    if search_text:
        if case_sensitive:
            occurrence_counts = comments_df["댓글"].str.count(
                re.escape(search_text)
            )
            matched_mask = comments_df["댓글"].str.contains(
                re.escape(search_text),
                regex=True,
                na=False,
            )
        else:
            occurrence_counts = comments_df["댓글"].str.count(
                re.compile(
                    re.escape(search_text),
                    flags=re.IGNORECASE,
                )
            )
            matched_mask = comments_df["댓글"].str.contains(
                re.escape(search_text),
                case=False,
                regex=True,
                na=False,
            )

        total_occurrences = int(occurrence_counts.sum())
        matched_comments = comments_df.loc[matched_mask].copy()

        search_metric1, search_metric2 = st.columns(2)

        with search_metric1:
            st.metric("문자열 출현 횟수", f"{total_occurrences:,}회")

        with search_metric2:
            st.metric(
                "문자열이 포함된 댓글",
                f"{len(matched_comments):,}개",
            )

        if matched_comments.empty:
            st.info("입력한 문자열이 사용된 댓글이 없습니다.")
        else:
            st.subheader("검색 문자열이 사용된 댓글")

            for row_number, (_, row) in enumerate(
                matched_comments.iterrows(),
                start=1,
            ):
                author = row.get("작성자 ID", "작성자 정보 없음")
                published_at = row.get("작성 일시", "")
                likes = row.get("좋아요", row.get("좋아요 수", 0))
                comment_text = row.get("댓글", "")

                # HTML 특수문자가 화면 구조를 깨뜨리지 않도록 변환합니다.
                safe_author = (
                    str(author)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                safe_date = (
                    str(published_at)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                safe_comment = (
                    str(comment_text)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )

                st.markdown(
                    f"""
                    <div class="comment-card">
                        <div class="comment-meta">
                            {row_number}. {safe_author}
                            · {safe_date}
                            · 좋아요 {likes}
                        </div>
                        <div class="comment-text">{safe_comment}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

