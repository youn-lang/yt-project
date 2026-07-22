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
    st.metric("형태소 종류 (Type)", f"{len(lexical_df):,}개")

with result_col2:
    st.metric("전체 출현 형태소 (Token)", f"{lexical_df['빈도수'].sum():,}개")

st.caption(
    "형태소는 형태소 분석기가 나눈 최소 분석 단위입니다. "
    "Type은 서로 다른 형태소 항목의 수이고, Token은 중복을 포함한 전체 출현 횟수입니다."
)

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
            "단어": st.column_config.TextColumn("형태소", width="medium"),
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
        "이 영역에서는 형태소 분석 결과를 사용하되, 화면에는 기본형을 기준으로 한 "
        "단어 목록으로 표시합니다. 영문 알파벳 한 글자 단어는 자동으로 제외합니다."
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

# 같은 형태라도 품사가 다르면 서로 다른 분석 항목으로 유지합니다.
# 예: "하/동사 파생 접미사"와 "하/형용사 파생 접미사"를 별도로 집계합니다.
frequency_df = (
    frequency_df.groupby(
        ["단어", "품사", "기본형"],
        as_index=False,
        dropna=False,
    )["빈도수"]
    .sum()
    .sort_values(
        ["빈도수", "단어", "품사"],
        ascending=[False, True, True],
    )
    .head(int(top_n))
)

# 출현 빈도 분석에서는 기본형을 '단어'로 표시합니다.
# 같은 기본형이 여러 품사로 나타나면 그래프에서 구분할 수 있도록 품사를 덧붙입니다.
word_pos_counts = frequency_df.groupby("기본형")["품사"].transform("nunique")
frequency_df["표시 단어"] = frequency_df["기본형"]
frequency_df.loc[word_pos_counts > 1, "표시 단어"] = (
    frequency_df.loc[word_pos_counts > 1, "기본형"]
    + " · "
    + frequency_df.loc[word_pos_counts > 1, "품사"]
)

if frequency_df.empty:
    st.warning("현재 조건에 표시할 단어가 없습니다.")
else:
    list_col, chart_col = st.columns([0.8, 1.7])

    with list_col:
        frequency_table_df = frequency_df[
            ["기본형", "빈도수", "품사", "단어"]
        ].rename(
            columns={
                "기본형": "단어",
                "단어": "분석된 형태소",
            }
        )

        st.dataframe(
            frequency_table_df,
            use_container_width=True,
            hide_index=True,
            height=max(300, min(680, 42 * len(frequency_df) + 38)),
            column_config={
                "단어": st.column_config.TextColumn("단어", width="medium"),
                "빈도수": st.column_config.NumberColumn(
                    "빈도수",
                    format="%d",
                    width="small",
                ),
                "품사": st.column_config.TextColumn("품사", width="medium"),
                "분석된 형태소": st.column_config.TextColumn(
                    "분석된 형태소",
                    width="medium",
                ),
            },
        )

    with chart_col:
        # 그래프에서 빈도가 큰 단어가 위에 오도록 역순으로 전달합니다.
        chart_df = frequency_df.iloc[::-1].copy()

        figure = px.bar(
            chart_df,
            x="빈도수",
            y="표시 단어",
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
            xaxis_title="단어 출현 빈도수",
            yaxis_title="단어",
            yaxis_categoryorder="array",
            yaxis_categoryarray=chart_df["표시 단어"].tolist(),
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
# 6. 품사 분석
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">3</span>
        품사 분석
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "세부 품사명을 한꺼번에 나열하지 않고, 명사·동사·조사처럼 "
    "큰 범주로 묶어 선택할 수 있습니다. 표에서는 실제 세부 품사도 함께 표시합니다."
)

# 형태소 분석기에 사용된 세부 품사를 비전공자가 고르기 쉬운 큰 범주로 묶습니다.
POS_GROUPS = {
    "명사": {
        "일반 명사",
        "고유 명사",
        "의존 명사",
    },
    "대명사·수사": {
        "대명사",
        "수사",
    },
    "동사": {
        "동사",
        "보조 용언",
        "긍정 지정사",
        "부정 지정사",
    },
    "형용사": {
        "형용사",
    },
    "관형사": {
        "관형사",
    },
    "부사": {
        "일반 부사",
        "접속 부사",
    },
    "감탄사": {
        "감탄사",
    },
    "조사": {
        "주격 조사",
        "보격 조사",
        "관형격 조사",
        "목적격 조사",
        "부사격 조사",
        "호격 조사",
        "인용격 조사",
        "보조사",
        "접속 조사",
    },
    "어미": {
        "선어말 어미",
        "종결 어미",
        "연결 어미",
        "명사형 전성 어미",
        "관형형 전성 어미",
    },
    "접사·어근": {
        "접두사",
        "명사 파생 접미사",
        "동사 파생 접미사",
        "형용사 파생 접미사",
        "어근",
        "덧붙은 받침",
    },
    "영문": {
        "영문",
    },
    "숫자": {
        "숫자",
    },
    "이모지": {
        "이모지",
    },
    "문장부호": {
        "마침표·물음표·느낌표",
        "쉼표·가운뎃점·콜론",
        "괄호·따옴표",
        "여는 괄호·따옴표",
        "닫는 괄호·따옴표",
        "줄임표",
        "붙임표",
        "기타 기호",
    },
    "기타": {
        "한자",
        "URL",
        "이메일",
        "해시태그",
        "멘션",
        "일련번호",
        "사용자 정의어",
    },
}

# 실제 분석 결과에 존재하는 품사만 포함된 그룹을 선택지로 제공합니다.
existing_pos = set(lexical_df["품사"].dropna().astype(str))
available_pos_groups = [
    group_name
    for group_name, detailed_pos in POS_GROUPS.items()
    if existing_pos.intersection(detailed_pos)
]

if not available_pos_groups:
    st.info("현재 분석 결과에서 선택할 수 있는 품사를 찾지 못했습니다.")
else:
    selection_col1, selection_col2 = st.columns(2)

    with selection_col1:
        selected_pos_group = st.selectbox(
            "품사 범주",
            options=available_pos_groups,
            index=0,
            help="명사·동사·조사처럼 큰 품사 범주를 먼저 선택합니다.",
        )

    # 선택한 큰 범주 안에서 실제 데이터에 존재하는 세부 품사만 추립니다.
    detailed_pos_options = sorted(
        existing_pos.intersection(POS_GROUPS[selected_pos_group])
    )

    with selection_col2:
        selected_detailed_pos = st.selectbox(
            "세부 품사",
            options=["전체"] + detailed_pos_options,
            index=0,
            help="전체를 선택하면 해당 범주의 모든 세부 품사를 함께 분석합니다.",
        )

    # '전체'를 선택하면 큰 범주 안의 모든 세부 품사를 사용합니다.
    # 개별 세부 품사를 선택하면 해당 품사만 남깁니다.
    if selected_detailed_pos == "전체":
        selected_pos_set = set(detailed_pos_options)
    else:
        selected_pos_set = {selected_detailed_pos}

    pos_df = lexical_df[
        lexical_df["품사"].isin(selected_pos_set)
    ].copy()

    # 품사 분석 화면에서는 기본형을 단어로 표시합니다.
    # 같은 기본형이라도 세부 품사가 다르면 별도의 단어 항목으로 유지합니다.
    pos_word_df = (
        pos_df.groupby(
            ["기본형", "품사"],
            as_index=False,
            dropna=False,
        )["빈도수"]
        .sum()
        .sort_values(
            ["빈도수", "기본형", "품사"],
            ascending=[False, True, True],
        )
        .rename(columns={"기본형": "단어"})
        .reset_index(drop=True)
    )

    pos_metric_col1, pos_metric_col2, pos_metric_col3 = st.columns(3)

    with pos_metric_col1:
        selected_pos_label = (
            selected_pos_group
            if selected_detailed_pos == "전체"
            else selected_detailed_pos
        )

        st.metric(
            "선택한 품사",
            selected_pos_label,
        )

    with pos_metric_col2:
        st.metric(
            "단어 종류 (Type)",
            f"{len(pos_word_df):,}개",
        )

    with pos_metric_col3:
        st.metric(
            "출현 빈도 합계 (Token)",
            f"{int(pos_word_df['빈도수'].sum()):,}회",
        )

    detailed_pos_found = sorted(pos_word_df["품사"].unique().tolist())

    if detailed_pos_found:
        st.caption(
            "분석에 포함된 세부 품사: "
            + ", ".join(detailed_pos_found)
        )

    if pos_word_df.empty:
        st.info("선택한 품사 범주에 해당하는 단어가 없습니다.")
    else:
        st.dataframe(
            pos_word_df[["단어", "빈도수", "품사"]],
            use_container_width=True,
            hide_index=True,
            height=min(620, max(260, 42 * len(pos_word_df) + 38)),
            column_config={
                "단어": st.column_config.TextColumn(
                    "단어",
                    width="large",
                ),
                "빈도수": st.column_config.NumberColumn(
                    "빈도수",
                    format="%d",
                    width="small",
                ),
                "품사": st.column_config.TextColumn(
                    "세부 품사",
                    width="medium",
                ),
            },
        )
