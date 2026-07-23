import io
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import spacy
import streamlit as st
from wordcloud import WordCloud
from kiwipiepy import Kiwi
from sudachipy import dictionary, tokenizer


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

    [data-testid="stDataFrame"] {
        min-width: 100%;
    }

    [data-testid="stDataFrame"] [role="columnheader"]:first-child,
    [data-testid="stDataFrame"] [role="gridcell"]:first-child {
        min-width: 140px;
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
            수집한 댓글을 형태소 단위로 분석하고 품사와 빈도 등의 사용 양상을 확인합니다.
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
        "분석할 댓글 데이터가 없습니다. "
        "먼저 메인 페이지에서 분석 언어를 선택하고 유튜브 댓글을 불러와 주세요."
    )
    st.stop()

comments_df["댓글"] = comments_df["댓글"].fillna("").astype(str)

# ------------------------------------------------------------
# 3. 분석 언어와 형태소 분석기 준비
# ------------------------------------------------------------
analysis_language = st.session_state.get(
    "selected_analysis_language"
)

if analysis_language not in {"한국어", "일본어", "영어"}:
    st.warning(
        "분석 언어 정보가 없습니다. 메인 페이지에서 분석 언어를 선택한 뒤 "
        "댓글을 다시 불러와 주세요."
    )
    st.stop()

language_metric_col1, language_metric_col2, language_metric_col3 = st.columns(3)

with language_metric_col1:
    st.metric("분석 언어", analysis_language)

with language_metric_col2:
    st.metric("분석 대상 댓글", f"{len(comments_df):,}개")

with language_metric_col3:
    non_empty_count = comments_df["댓글"].str.strip().ne("").sum()
    st.metric("내용이 있는 댓글", f"{non_empty_count:,}개")


@st.cache_resource
def load_kiwi() -> Kiwi:
    """한국어 형태소 분석기 Kiwi를 한 번만 불러옵니다."""
    return Kiwi()


@st.cache_resource
def load_sudachi():
    """일본어 형태소 분석기 SudachiPy를 한 번만 불러옵니다."""
    return dictionary.Dictionary().create()


@st.cache_resource
def load_spacy_english():
    """spaCy 영어 모델을 한 번만 불러옵니다."""
    return spacy.load("en_core_web_sm")


# Kiwi의 세부 품사 태그를 한국어 명칭으로 표시합니다.
KOREAN_POS_NAMES = {
    "NNG": "일반 명사", "NNP": "고유 명사", "NNB": "의존 명사",
    "NR": "수사", "NP": "대명사", "VV": "동사", "VA": "형용사",
    "VX": "보조 용언", "VCP": "긍정 지정사", "VCN": "부정 지정사",
    "MM": "관형사", "MAG": "일반 부사", "MAJ": "접속 부사",
    "IC": "감탄사", "JKS": "주격 조사", "JKC": "보격 조사",
    "JKG": "관형격 조사", "JKO": "목적격 조사", "JKB": "부사격 조사",
    "JKV": "호격 조사", "JKQ": "인용격 조사", "JX": "보조사",
    "JC": "접속 조사", "EP": "선어말 어미", "EF": "종결 어미",
    "EC": "연결 어미", "ETN": "명사형 전성 어미", "ETM": "관형형 전성 어미",
    "XPN": "접두사", "XSN": "명사 파생 접미사", "XSV": "동사 파생 접미사",
    "XSA": "형용사 파생 접미사", "XR": "어근",
    "SF": "마침표·물음표·느낌표", "SP": "쉼표·가운뎃점·콜론",
    "SS": "괄호·따옴표", "SSO": "여는 괄호·따옴표", "SSC": "닫는 괄호·따옴표",
    "SE": "줄임표", "SO": "붙임표", "SW": "기타 기호",
    "SL": "영문", "SH": "한자", "SN": "숫자",
    "W_URL": "URL", "W_EMAIL": "이메일", "W_HASHTAG": "해시태그",
    "W_MENTION": "멘션", "W_SERIAL": "일련번호", "Z_CODA": "덧붙은 받침",
    "USER0": "사용자 정의어",
}

# 한국어 품사 화면의 큰 범주입니다.
KOREAN_POS_GROUPS = {
    "명사": {"NNG", "NNP", "NNB"},
    "대명사·수사": {"NP", "NR"},
    "동사": {"VV", "VX", "VCP", "VCN"},
    "형용사": {"VA"},
    "관형사": {"MM"},
    "부사": {"MAG", "MAJ"},
    "감탄사": {"IC"},
    "조사": {"JKS", "JKC", "JKG", "JKO", "JKB", "JKV", "JKQ", "JX", "JC"},
    "어미": {"EP", "EF", "EC", "ETN", "ETM"},
    "접사·어근": {"XPN", "XSN", "XSV", "XSA", "XR", "Z_CODA"},
    "영문": {"SL"},
    "한자": {"SH"},
    "숫자": {"SN"},
    "문장부호": {"SF", "SP", "SS", "SSO", "SSC", "SE", "SO"},
    "기타 기호": {"SW"},
    "웹 표현": {"W_URL", "W_EMAIL", "W_HASHTAG", "W_MENTION", "W_SERIAL"},
    "기타": {"USER0"},
}

# 품사 선택 메뉴에 사용할 언어별 표시 순서입니다.
# 한국어는 내용어를 먼저, 조사·어미 등의 기능어를 뒤에 배치합니다.
# 영어 품사 대분류는 내용어를 먼저, 기능어를 뒤에 배치합니다.
ENGLISH_POS_ORDER = [
    "NOUN",
    "PROPN",
    "VERB",
    "ADJ",
    "ADV",
    "PRON",
    "NUM",
    "INTJ",
    "AUX",
    "DET",
    "ADP",
    "PART",
    "CCONJ",
    "SCONJ",
    "PUNCT",
    "SYM",
    "X",
]

# spaCy의 영어 세부 품사는 Penn Treebank 태그를 기준으로 배열합니다.
ENGLISH_DETAILED_POS_ORDER = {
    "NOUN": ["NN", "NNS"],
    "PROPN": ["NNP", "NNPS"],
    "VERB": ["VB", "VBP", "VBZ", "VBD", "VBG", "VBN"],
    "ADJ": ["JJ", "JJR", "JJS"],
    "ADV": ["RB", "RBR", "RBS", "WRB"],
    "PRON": ["PRP", "PRP$", "WP", "WP$"],
    "NUM": ["CD"],
    "INTJ": ["UH"],
    "AUX": ["MD"],
    "DET": ["DT", "PDT", "WDT"],
    "ADP": ["IN"],
    "PART": ["RP", "TO", "POS"],
    "CCONJ": ["CC"],
    "SCONJ": ["IN"],
    "PUNCT": [".", ",", ":", "-LRB-", "-RRB-", "``", "''"],
    "SYM": ["SYM"],
    "X": ["FW", "LS"],
}


KOREAN_POS_ORDER = [
    "명사",
    "대명사·수사",
    "동사",
    "형용사",
    "관형사",
    "부사",
    "감탄사",
    "접사·어근",
    "조사",
    "어미",
    "영문",
    "한자",
    "숫자",
    "이모지",
    "문장부호",
    "기타 기호",
    "웹 표현",
    "기타",
]

# 한국어 세부 품사는 실제 댓글에서 상대적으로 자주 관찰되는 항목을 앞에 둡니다.
KOREAN_DETAILED_POS_ORDER = {
    "명사": ["일반 명사", "고유 명사", "의존 명사"],
    "대명사·수사": ["대명사", "수사"],
    "동사": ["동사", "보조 용언", "긍정 지정사", "부정 지정사"],
    "형용사": ["형용사"],
    "관형사": ["관형사"],
    "부사": ["일반 부사", "접속 부사"],
    "감탄사": ["감탄사"],
    "접사·어근": [
        "명사 파생 접미사",
        "동사 파생 접미사",
        "형용사 파생 접미사",
        "접두사",
        "어근",
        "덧붙은 받침",
    ],
    "조사": [
        "보조사",
        "주격 조사",
        "목적격 조사",
        "부사격 조사",
        "관형격 조사",
        "접속 조사",
        "인용격 조사",
        "보격 조사",
        "호격 조사",
    ],
    "어미": [
        "종결 어미",
        "연결 어미",
        "선어말 어미",
        "관형형 전성 어미",
        "명사형 전성 어미",
    ],
    "문장부호": [
        "마침표·물음표·느낌표",
        "쉼표·가운뎃점·콜론",
        "괄호·따옴표",
        "여는 괄호·따옴표",
        "닫는 괄호·따옴표",
        "줄임표",
        "붙임표",
    ],
    "웹 표현": ["URL", "해시태그", "멘션", "이메일", "일련번호"],
}

# 일본어 대분류는 한국어 배열과 가능한 한 대응하도록 구성합니다.
# 내용어를 앞에, 조사·조동사 같은 기능어를 뒤에 둡니다.
JAPANESE_POS_ORDER = [
    "名詞",
    "代名詞",
    "動詞",
    "形容詞",
    "形状詞",
    "連体詞",
    "副詞",
    "接続詞",
    "感動詞",
    "接頭辞",
    "接尾辞",
    "助詞",
    "助動詞",
    "絵文字",
    "記号",
    "補助記号",
    "空白",
    "未分類",
]

# Sudachi 세부 품사는 일본어 내부에서 일반적으로 자주 나타나는 순서를 우선합니다.
# 정확히 일치하지 않는 새 항목은 같은 대분류의 뒤쪽에 자동으로 배치됩니다.
JAPANESE_DETAILED_POS_ORDER = {
    "名詞": [
        "名詞-普通名詞-一般",
        "名詞-固有名詞-一般",
        "名詞-普通名詞-サ変可能",
        "名詞-普通名詞-形状詞可能",
        "名詞-数詞",
        "名詞-固有名詞-人名",
        "名詞-固有名詞-地名",
        "名詞-助動詞語幹",
    ],
    "代名詞": ["代名詞"],
    "動詞": [
        "動詞-一般",
        "動詞-非自立可能",
    ],
    "形容詞": [
        "形容詞-一般",
        "形容詞-非自立可能",
    ],
    "形状詞": [
        "形状詞-一般",
        "形状詞-タリ",
        "形状詞-助動詞語幹",
    ],
    "連体詞": ["連体詞"],
    "副詞": ["副詞"],
    "接続詞": ["接続詞"],
    "感動詞": [
        "感動詞-一般",
        "感動詞-フィラー",
    ],
    "接頭辞": ["接頭辞"],
    "接尾辞": [
        "接尾辞-名詞的-一般",
        "接尾辞-名詞的-サ変可能",
        "接尾辞-形容詞的",
        "接尾辞-動詞的",
    ],
    "助詞": [
        "助詞-格助詞",
        "助詞-係助詞",
        "助詞-接続助詞",
        "助詞-副助詞",
        "助詞-終助詞",
        "助詞-準体助詞",
    ],
    "助動詞": ["助動詞"],
    "記号": ["記号-一般", "記号-文字"],
    "補助記号": [
        "補助記号-句点",
        "補助記号-読点",
        "補助記号-括弧開",
        "補助記号-括弧閉",
        "補助記号-一般",
        "補助記号-AA-一般",
        "補助記号-AA-顔文字",
    ],
}


def order_by_priority(values: list[str], priority: list[str]) -> list[str]:
    """우선순위표에 있는 항목을 먼저 배치하고 나머지는 이름순으로 붙입니다."""
    unique_values = list(dict.fromkeys(str(value) for value in values))
    priority_index = {value: index for index, value in enumerate(priority)}

    return sorted(
        unique_values,
        key=lambda value: (
            priority_index.get(value, len(priority)),
            value,
        ),
    )


def ordered_pos_groups(language: str, values: list[str]) -> list[str]:
    """선택한 분석 언어에 맞게 품사 대분류 순서를 정합니다."""
    if language == "한국어":
        return order_by_priority(values, KOREAN_POS_ORDER)

    if language == "일본어":
        return order_by_priority(values, JAPANESE_POS_ORDER)

    if language == "영어":
        return order_by_priority(values, ENGLISH_POS_ORDER)

    return sorted(values)


def ordered_detailed_pos(
    language: str,
    pos_group: str,
    values: list[str],
) -> list[str]:
    """선택한 언어와 대분류에 맞게 세부 품사 순서를 정합니다."""
    if language == "한국어":
        priority = KOREAN_DETAILED_POS_ORDER.get(pos_group, [])
        return order_by_priority(values, priority)

    if language == "일본어":
        priority = JAPANESE_DETAILED_POS_ORDER.get(pos_group, [])
        return order_by_priority(values, priority)

    if language == "영어":
        priority = ENGLISH_DETAILED_POS_ORDER.get(pos_group, [])
        return order_by_priority(values, priority)

    return sorted(values)

EMOJI_PATTERN = re.compile(
    "["
    "\\U0001F1E6-\\U0001F1FF"
    "\\U0001F300-\\U0001F5FF"
    "\\U0001F600-\\U0001F64F"
    "\\U0001F680-\\U0001F6FF"
    "\\U0001F700-\\U0001F77F"
    "\\U0001F780-\\U0001F7FF"
    "\\U0001F800-\\U0001F8FF"
    "\\U0001F900-\\U0001F9FF"
    "\\U0001FA00-\\U0001FAFF"
    "\\u2600-\\u26FF"
    "\\u2700-\\u27BF"
    "]"
)
EMOJI_SEQUENCE_PATTERN = re.compile(
    r"(?:" + EMOJI_PATTERN.pattern + r")(?:[\\uFE0F\\u200D\\U0001F3FB-\\U0001F3FF]*"
    + EMOJI_PATTERN.pattern + r")*"
)


def make_korean_base_form(form: str, tag: str) -> str:
    if tag.startswith(("VV", "VA", "VX", "VCP", "VCN")):
        return f"{form}다"
    if tag == "SL":
        return form.lower()
    return form


def korean_major_pos(tag: str) -> str:
    """Kiwi 태그를 한국어 품사 대분류로 변환합니다."""
    for group_name, tags in KOREAN_POS_GROUPS.items():
        if tag in tags:
            return group_name
    return "기타"


def japanese_detailed_pos(pos_tuple: tuple[str, ...]) -> str:
    """Sudachi 품사 배열에서 의미 있는 앞부분을 세부 품사명으로 만듭니다."""
    meaningful = [item for item in pos_tuple[:3] if item and item != "*"]
    return "-".join(meaningful) if meaningful else "未分類"


def katakana_to_hiragana(text: str) -> str:
    """가타카나 읽기를 히라가나로 통일합니다."""
    converted = []

    for character in text:
        code_point = ord(character)

        if 0x30A1 <= code_point <= 0x30F6:
            converted.append(chr(code_point - 0x60))
        else:
            converted.append(character)

    return "".join(converted)


# Sudachi 사전에서 별도 기본형으로 처리될 수 있는 구어형·표기 변이를
# 연구 목적에 맞는 대표 기본형으로 통합합니다.
# 필요하면 이 사전에 항목을 계속 추가할 수 있습니다.
JAPANESE_LEMMA_ALIASES = {
    "みる": "見る",
    "見れる": "見る",
    "みれる": "見る",
}

JAPANESE_READING_ALIASES = {
    "みれる": "みる",
}


def normalize_japanese_lemma(
    dictionary_form: str,
    normalized_form: str,
    major_pos: str,
) -> str:
    """
    일본어 기본형을 집계용 대표형으로 정규화합니다.

    1. Sudachi의 normalized_form을 우선 사용합니다.
    2. 동사·형용사류는 별도 대응표를 적용합니다.
    3. 대응표에 없는 항목은 Sudachi의 정규화형을 유지합니다.
    """
    candidate = normalized_form

    if not candidate or candidate == "*":
        candidate = dictionary_form

    if not candidate or candidate == "*":
        candidate = ""

    predicate_categories = {
        "動詞",
        "形容詞",
        "形状詞",
        "助動詞",
    }

    if major_pos in predicate_categories:
        return JAPANESE_LEMMA_ALIASES.get(candidate, candidate)

    return candidate


def append_emoji_rows(rows: list[dict], form: str, language: str) -> str:
    """토큰 안의 이모지를 독립 항목으로 기록하고 남은 문자열을 반환합니다."""
    for emoji_text in EMOJI_SEQUENCE_PATTERN.findall(form):
        rows.append(
            {
                "언어": language,
                "형태소": emoji_text,
                "기본형": emoji_text,
                "정규화형": emoji_text,
                "읽기": "",
                "표기 변이": emoji_text,
                "품사 범주": "이모지" if language != "일본어" else "絵文字",
                "세부 품사": "이모지" if language != "일본어" else "絵文字",
                "원래 품사": "EMOJI",
            }
        )
    return EMOJI_SEQUENCE_PATTERN.sub("", form).strip()


def analyze_korean_text(text: str, rows: list[dict]) -> None:
    kiwi = load_kiwi()
    for token in kiwi.tokenize(text):
        form = token.form.strip()
        tag = token.tag
        if not form:
            continue

        remaining = append_emoji_rows(rows, form, "한국어")
        if not remaining:
            continue

        display_form = form.lower() if tag == "SL" else form
        rows.append(
            {
                "언어": "한국어",
                "형태소": display_form,
                "기본형": make_korean_base_form(form, tag),
                "정규화형": make_korean_base_form(form, tag),
                "읽기": "",
                "표기 변이": display_form,
                "품사 범주": korean_major_pos(tag),
                "세부 품사": KOREAN_POS_NAMES.get(tag, tag),
                "원래 품사": tag,
            }
        )


def analyze_japanese_text(text: str, rows: list[dict]) -> None:
    sudachi = load_sudachi()

    for morpheme in sudachi.tokenize(
        text,
        tokenizer.Tokenizer.SplitMode.B,
    ):
        form = morpheme.surface().strip()

        if not form:
            continue

        remaining = append_emoji_rows(rows, form, "일본어")

        if not remaining:
            continue

        pos_tuple = tuple(morpheme.part_of_speech())
        major_pos = pos_tuple[0] if pos_tuple else "未分類"
        detailed_pos = japanese_detailed_pos(pos_tuple)
        original_pos = ",".join(pos_tuple)

        # 공백은 분석 결과에서 제외합니다.
        if major_pos == "空白":
            continue

        dictionary_form = morpheme.dictionary_form()

        if not dictionary_form or dictionary_form == "*":
            dictionary_form = form

        normalized_form = morpheme.normalized_form()

        if not normalized_form or normalized_form == "*":
            normalized_form = dictionary_form

        reading = morpheme.reading_form()

        if not reading or reading == "*":
            reading = form

        reading_hiragana = katakana_to_hiragana(reading)
        reading_hiragana = JAPANESE_READING_ALIASES.get(
            reading_hiragana,
            reading_hiragana,
        )

        canonical_lemma = normalize_japanese_lemma(
            dictionary_form=dictionary_form,
            normalized_form=normalized_form,
            major_pos=major_pos,
        )

        if not canonical_lemma:
            canonical_lemma = dictionary_form

        rows.append(
            {
                "언어": "일본어",
                "형태소": form,
                "기본형": canonical_lemma,
                "정규화형": normalized_form,
                "읽기": reading_hiragana,
                "표기 변이": form,
                "품사 범주": major_pos,
                "세부 품사": detailed_pos,
                "원래 품사": original_pos,
            }
        )


def analyze_english_text(text: str, rows: list[dict]) -> None:
    """spaCy로 영어 형태소, 기본형, 품사를 분석합니다."""
    nlp = load_spacy_english()
    document = nlp(text)

    for token in document:
        if token.is_space:
            continue

        form = token.text.strip()
        if not form:
            continue

        remaining = append_emoji_rows(rows, form, "영어")
        if not remaining:
            continue

        lemma = token.lemma_.strip()
        if not lemma or lemma == "-PRON-":
            lemma = form

        normalized_lemma = lemma.lower()

        rows.append(
            {
                "언어": "영어",
                "형태소": form,
                "기본형": normalized_lemma,
                "정규화형": normalized_lemma,
                "읽기": "",
                "표기 변이": form,
                "품사 범주": token.pos_ or "X",
                "세부 품사": token.tag_ or "X",
                "원래 품사": (
                    f"POS={token.pos_}; "
                    f"TAG={token.tag_}; "
                    f"MORPH={token.morph}"
                ),
            }
        )


def build_lexical_dataframe(
    token_df: pd.DataFrame,
    language: str,
) -> pd.DataFrame:
    """
    토큰 단위 데이터프레임에서 화면 표시용 집계 데이터프레임을 만듭니다.

    token_df에는 댓글별 출현 순서와 실제 표기를 보존하고,
    lexical_df에는 기존 화면에서 사용하던 형태소·기본형·품사별 빈도를 저장합니다.
    """
    columns = [
        "언어",
        "형태소",
        "빈도수",
        "품사 범주",
        "세부 품사",
        "기본형",
        "정규화형",
        "읽기",
        "표기 변이",
        "원래 품사",
    ]

    if token_df.empty:
        return pd.DataFrame(columns=columns)

    if language == "일본어":
        group_columns = [
            "언어",
            "기본형",
            "품사 범주",
            "세부 품사",
            "원래 품사",
        ]

        grouped_rows: list[dict] = []

        for group_values, group_df in token_df.groupby(
            group_columns,
            dropna=False,
            sort=False,
        ):
            (
                group_language,
                base_form,
                major_pos,
                detailed_pos,
                original_pos,
            ) = group_values

            variants = sorted(
                {
                    str(value)
                    for value in group_df["표기 변이"]
                    if str(value).strip()
                }
            )
            normalized_variants = sorted(
                {
                    str(value)
                    for value in group_df["정규화형"]
                    if str(value).strip()
                }
            )
            readings = sorted(
                {
                    str(value)
                    for value in group_df["읽기"]
                    if str(value).strip()
                }
            )

            grouped_rows.append(
                {
                    "언어": group_language,
                    "형태소": base_form,
                    "빈도수": len(group_df),
                    "품사 범주": major_pos,
                    "세부 품사": detailed_pos,
                    "기본형": base_form,
                    "정규화형": " / ".join(normalized_variants),
                    "읽기": " / ".join(readings),
                    "표기 변이": " / ".join(variants),
                    "원래 품사": original_pos,
                }
            )

        result_df = pd.DataFrame(grouped_rows)

    else:
        result_df = (
            token_df.groupby(
                [
                    "언어",
                    "형태소",
                    "품사 범주",
                    "세부 품사",
                    "기본형",
                    "정규화형",
                    "읽기",
                    "표기 변이",
                    "원래 품사",
                ],
                as_index=False,
                dropna=False,
            )
            .size()
            .rename(columns={"size": "빈도수"})
        )

    result_df = (
        result_df.sort_values(
            ["빈도수", "형태소", "품사 범주", "세부 품사"],
            ascending=[False, True, True, True],
        )
        .reset_index(drop=True)
    )

    return result_df[columns]


def analyze_comments(
    comment_series: pd.Series,
    language: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    댓글을 한 번만 분석해 토큰 단위 token_df와 집계용 lexical_df를 함께 만듭니다.

    token_df의 댓글 ID와 토큰 순서는 이후 공기어, N-gram, KWIC 분석에 사용할 수 있습니다.
    """
    token_rows: list[dict] = []

    for comment_id, raw_text in enumerate(comment_series):
        text = str(raw_text)
        comment_rows: list[dict] = []

        if language == "한국어":
            analyze_korean_text(text, comment_rows)
        elif language == "일본어":
            analyze_japanese_text(text, comment_rows)
        else:
            analyze_english_text(text, comment_rows)

        for token_index, row in enumerate(comment_rows):
            token_rows.append(
                {
                    "댓글 ID": comment_id,
                    "토큰 순서": token_index,
                    "댓글 원문": text,
                    **row,
                }
            )

    token_columns = [
        "댓글 ID",
        "토큰 순서",
        "댓글 원문",
        "언어",
        "형태소",
        "기본형",
        "정규화형",
        "읽기",
        "표기 변이",
        "품사 범주",
        "세부 품사",
        "원래 품사",
    ]

    if not token_rows:
        empty_token_df = pd.DataFrame(columns=token_columns)
        empty_lexical_df = build_lexical_dataframe(
            empty_token_df,
            language,
        )
        return empty_token_df, empty_lexical_df

    token_df = (
        pd.DataFrame(token_rows)[token_columns]
        .sort_values(["댓글 ID", "토큰 순서"])
        .reset_index(drop=True)
    )

    lexical_df = build_lexical_dataframe(token_df, language)
    return token_df, lexical_df


@st.cache_data(show_spinner=False)
def cached_analyze_comments(
    comment_tuple: tuple[str, ...],
    language: str,
    schema_version: str = "token-df-v1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """댓글 분석 결과를 데이터 구조 버전과 함께 캐시합니다."""
    _ = schema_version
    return analyze_comments(pd.Series(comment_tuple), language)


# ------------------------------------------------------------
# Word Cloud용 보조 함수
# ------------------------------------------------------------
def find_wordcloud_font(language: str) -> str | None:
    """Streamlit Cloud와 일반 Linux 환경에서 사용할 글꼴을 찾습니다."""
    cjk_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    ]
    latin_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    candidates = cjk_candidates + latin_candidates if language in {"한국어", "일본어"} else latin_candidates + cjk_candidates

    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return None


def make_wordcloud_png(
    frequencies: dict[str, int],
    font_path: str | None,
    width: int,
    height: int,
    transparent: bool,
) -> tuple[WordCloud, bytes]:
    """빈도 사전으로 Word Cloud와 PNG 바이트를 생성합니다."""
    cloud = WordCloud(
        width=width,
        height=height,
        background_color=None if transparent else "white",
        mode="RGBA" if transparent else "RGB",
        font_path=font_path,
        max_words=len(frequencies),
        prefer_horizontal=0.9,
        relative_scaling=0.45,
        collocations=False,
        margin=4,
        random_state=42,
    ).generate_from_frequencies(frequencies)

    image = cloud.to_image()
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return cloud, buffer.getvalue()


analyzer_name = {
    "한국어": "Kiwi",
    "일본어": "SudachiPy (SplitMode.B)",
    "영어": "spaCy (en_core_web_sm)",
}[analysis_language]

with st.spinner(f"{analyzer_name}로 댓글 전체를 분석하는 중입니다..."):
    try:
        token_df, lexical_df = cached_analyze_comments(
            tuple(comments_df["댓글"].astype(str).tolist()),
            analysis_language,
        )
    except OSError:
        if analysis_language == "영어":
            st.error(
                "spaCy 영어 모델(en_core_web_sm)이 설치되지 않았습니다. "
                "requirements.txt에 spaCy와 영어 모델을 추가한 뒤 앱을 재부트해 주세요."
            )
            st.stop()
        raise

# 이후 공기어·특징어·AI 해설 페이지가 같은 분석 결과를 재사용할 수 있도록 저장합니다.
st.session_state["token_df"] = token_df
st.session_state["lexical_df"] = lexical_df
st.session_state["lexical_analysis_language"] = analysis_language


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

result_col1, result_col2, result_col3 = st.columns(3)
with result_col1:
    st.metric("형태소 종류 (Type)", f"{len(lexical_df):,}개")
with result_col2:
    st.metric("전체 출현 형태소 (Token)", f"{int(lexical_df['빈도수'].sum()):,}개")
with result_col3:
    st.metric("사용 분석기", analyzer_name)

if analysis_language == "일본어":
    st.caption(
        "일본어는 SudachiPy의 사전형과 정규화형을 사용해 활용형과 표기 변이를 통합합니다. "
        "예를 들어 見る·みる·見れる는 대표 기본형 見る로 집계하며, "
        "실제 댓글에 나온 형태는 '표기 변이' 열에 보존합니다. "
        "품사명과 원래 품사 배열은 Sudachi 체계를 그대로 유지합니다."
    )
elif analysis_language == "한국어":
    st.caption(
        "한국어 품사 범주와 세부 품사는 Kiwi 태그를 한국어 문법 범주로 정리해 표시하며, "
        "'원래 품사' 열에는 Kiwi 태그를 보존합니다."
    )
else:
    st.caption(
        "영어는 spaCy로 기본형, 품사 범주, 세부 품사를 분석하며 원래 품사 정보도 함께 보존합니다."
    )

csv_data = lexical_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "형태소 분석 결과 CSV 다운로드",
    data=csv_data,
    file_name=f"youtube_comment_lexical_analysis_{analysis_language}.csv",
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
            "언어": st.column_config.TextColumn("언어", width="small"),
            "형태소": st.column_config.TextColumn("형태소", width="medium"),
            "빈도수": st.column_config.NumberColumn("빈도수", format="%d", width="small"),
            "품사 범주": st.column_config.TextColumn("품사 범주", width="medium"),
            "세부 품사": st.column_config.TextColumn("세부 품사", width="large"),
            "기본형": st.column_config.TextColumn("대표 기본형", width="medium"),
            "정규화형": st.column_config.TextColumn("Sudachi 정규화형", width="medium"),
            "읽기": st.column_config.TextColumn("읽기", width="medium"),
            "표기 변이": st.column_config.TextColumn("표기 변이", width="large"),
            "원래 품사": st.column_config.TextColumn("원래 품사", width="large"),
        },
    )


# ------------------------------------------------------------
# 5. 품사 분석
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">2</span>
        품사 분석
    </div>
    """,
    unsafe_allow_html=True,
)

if analysis_language == "일본어":
    st.caption(
        "SudachiPy의 일본어 품사 대분류와 세부 품사를 그대로 선택합니다. "
        "예: 名詞 → 名詞-普通名詞-一般."
    )
elif analysis_language == "한국어":
    st.caption(
        "한국어 품사 범주를 먼저 고른 뒤 Kiwi의 세부 품사를 선택합니다."
    )
else:
    st.caption("spaCy의 영어 품사 범주와 Penn Treebank 세부 품사를 선택합니다.")

available_pos_groups = ordered_pos_groups(
    analysis_language,
    lexical_df["품사 범주"].dropna().unique().tolist(),
)

if not available_pos_groups:
    st.info("현재 분석 결과에서 선택할 수 있는 품사를 찾지 못했습니다.")
else:
    selection_col1, selection_col2, selection_col3 = st.columns([1, 1.25, 0.8])

    with selection_col1:
        selected_pos_group = st.selectbox(
            "품사 범주",
            available_pos_groups,
            key="language_specific_pos_group",
        )

    detailed_pos_options = ordered_detailed_pos(
        analysis_language,
        selected_pos_group,
        lexical_df.loc[
            lexical_df["품사 범주"] == selected_pos_group,
            "세부 품사",
        ].dropna().unique().tolist(),
    )

    with selection_col2:
        selected_detailed_pos = st.selectbox(
            "세부 품사",
            ["전체"] + detailed_pos_options,
            key="language_specific_detailed_pos",
        )

    with selection_col3:
        pos_top_n = st.number_input(
            "표시할 상위 단어 수",
            min_value=5,
            max_value=200,
            value=20,
            step=5,
            key="pos_top_n_language_specific",
        )

    pos_df = lexical_df[
        lexical_df["품사 범주"] == selected_pos_group
    ].copy()

    if selected_detailed_pos != "전체":
        pos_df = pos_df[pos_df["세부 품사"] == selected_detailed_pos]

    pos_word_df = (
        pos_df.groupby(
            ["기본형", "품사 범주", "세부 품사"],
            as_index=False,
            dropna=False,
        )["빈도수"]
        .sum()
        .sort_values(
            ["빈도수", "기본형", "세부 품사"],
            ascending=[False, True, True],
        )
        .rename(columns={"기본형": "단어"})
        .reset_index(drop=True)
    )

    pos_metric_col1, pos_metric_col2, pos_metric_col3 = st.columns(3)
    with pos_metric_col1:
        selected_label = (
            selected_pos_group
            if selected_detailed_pos == "전체"
            else selected_detailed_pos
        )
        st.metric("선택한 품사", selected_label)
    with pos_metric_col2:
        st.metric("단어 종류 (Type)", f"{len(pos_word_df):,}개")
    with pos_metric_col3:
        st.metric("출현 빈도 합계 (Token)", f"{int(pos_word_df['빈도수'].sum()):,}회")

    if pos_word_df.empty:
        st.info("선택한 품사에 해당하는 단어가 없습니다.")
    else:
        pos_display_df = pos_word_df.head(int(pos_top_n)).copy()
        duplicate_counts = pos_display_df.groupby("단어")["세부 품사"].transform("nunique")
        pos_display_df["표시 단어"] = pos_display_df["단어"]
        pos_display_df.loc[duplicate_counts > 1, "표시 단어"] = (
            pos_display_df.loc[duplicate_counts > 1, "단어"]
            + " · "
            + pos_display_df.loc[duplicate_counts > 1, "세부 품사"]
        )

        table_row_height = 35
        table_header_height = 38
        pos_table_height = table_header_height + table_row_height * len(pos_display_df) + 3

        pos_list_col, pos_chart_col = st.columns([1.2, 1.3])

        with pos_list_col:
            st.dataframe(
                pos_display_df[["단어", "빈도수", "세부 품사"]],
                use_container_width=True,
                hide_index=True,
                height=pos_table_height,
                row_height=table_row_height,
                column_config={
                    "단어": st.column_config.TextColumn("단어", width=None),
                    "빈도수": st.column_config.NumberColumn("빈도수", format="%d", width="small"),
                    "세부 품사": st.column_config.TextColumn("세부 품사", width="large"),
                },
            )

        with pos_chart_col:
            pos_chart_df = pos_display_df.iloc[::-1].copy()
            pos_figure = px.bar(
                pos_chart_df,
                x="빈도수",
                y="표시 단어",
                orientation="h",
                text="빈도수",
                hover_data={"품사 범주": True, "세부 품사": True},
            )
            pos_figure.update_traces(
                marker_color="#7d8d4d",
                textposition="outside",
                cliponaxis=False,
            )
            pos_figure.update_layout(
                height=max(430, 31 * len(pos_chart_df)),
                margin=dict(l=10, r=45, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="선택 품사의 출현 빈도수",
                yaxis_title="단어",
                yaxis_categoryorder="array",
                yaxis_categoryarray=pos_chart_df["표시 단어"].tolist(),
                font=dict(color="#24331f"),
            )
            pos_figure.update_xaxes(
                showgrid=True,
                gridcolor="rgba(125,141,77,0.16)",
            )
            st.plotly_chart(
                pos_figure,
                use_container_width=True,
                config={"displayModeBar": False},
            )


# ------------------------------------------------------------
# 6. 출현 빈도 분석
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">3</span>
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
        key="frequency_top_n_language_specific",
    )
    remove_symbols = st.checkbox(
        "문장부호와 기호 제외",
        value=True,
        key="remove_symbols_language_specific",
    )

    exclude_single_letter_english = False
    if analysis_language == "영어":
        exclude_single_letter_english = st.checkbox(
            "알파벳 한 글자 단어 제외",
            value=False,
            key="exclude_single_letter_english",
            help=(
                "기본값은 포함입니다. 체크하면 I와 a를 포함한 "
                "모든 알파벳 한 글자 단어를 출현 빈도 분석에서만 제외합니다."
            ),
        )

with frequency_col2:
    if analysis_language == "영어":
        st.caption(
            "영어 형태소와 품사 분석에는 한 글자 단어도 포함합니다. "
            "필요한 경우에만 왼쪽 옵션으로 빈도 목록에서 제외할 수 있습니다."
        )
    else:
        st.caption(
            "선택한 언어의 전체 품사를 대상으로 기본형 기준 단어 빈도를 표시합니다."
        )

frequency_df = lexical_df.copy()

if analysis_language == "영어" and exclude_single_letter_english:
    one_letter_english = frequency_df["기본형"].str.fullmatch(
        r"[A-Za-z]",
        na=False,
    )
    frequency_df = frequency_df[~one_letter_english]

if remove_symbols:
    if analysis_language == "한국어":
        excluded_categories = {"문장부호", "기타 기호"}
    elif analysis_language == "일본어":
        excluded_categories = {"補助記号", "記号", "空白"}
    else:
        excluded_categories = {"PUNCT", "SYM", "SPACE"}

    frequency_df = frequency_df[
        ~frequency_df["품사 범주"].isin(excluded_categories)
    ]

frequency_df = (
    frequency_df.groupby(
        ["기본형", "품사 범주", "세부 품사"],
        as_index=False,
        dropna=False,
    )["빈도수"]
    .sum()
    .sort_values(
        ["빈도수", "기본형", "세부 품사"],
        ascending=[False, True, True],
    )
    .head(int(top_n))
    .rename(columns={"기본형": "단어"})
)

duplicate_counts = frequency_df.groupby("단어")["세부 품사"].transform("nunique")
frequency_df["표시 단어"] = frequency_df["단어"]
frequency_df.loc[duplicate_counts > 1, "표시 단어"] = (
    frequency_df.loc[duplicate_counts > 1, "단어"]
    + " · "
    + frequency_df.loc[duplicate_counts > 1, "세부 품사"]
)

if frequency_df.empty:
    st.warning("현재 조건에 표시할 단어가 없습니다.")
else:
    list_col, chart_col = st.columns([1.05, 1.45])

    with list_col:
        frequency_table_df = frequency_df[
            ["단어", "빈도수", "품사 범주", "세부 품사"]
        ]
        frequency_row_height = 35
        frequency_table_height = 38 + frequency_row_height * len(frequency_table_df) + 3
        st.dataframe(
            frequency_table_df,
            use_container_width=True,
            hide_index=True,
            height=frequency_table_height,
            row_height=frequency_row_height,
            column_config={
                "단어": st.column_config.TextColumn("단어", width=None),
                "빈도수": st.column_config.NumberColumn("빈도수", format="%d", width="small"),
                "품사 범주": st.column_config.TextColumn("품사 범주", width="medium"),
                "세부 품사": st.column_config.TextColumn("세부 품사", width="large"),
            },
        )

    with chart_col:
        chart_df = frequency_df.iloc[::-1].copy()
        figure = px.bar(
            chart_df,
            x="빈도수",
            y="표시 단어",
            orientation="h",
            text="빈도수",
            hover_data={"품사 범주": True, "세부 품사": True},
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
# 7. Word Cloud
# ------------------------------------------------------------
st.markdown(
    """
    <div class="section-label">
        <span class="section-number">4</span>
        Word Cloud
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "선택한 품사 범주에 속하는 단어만 사용해 발표 도입부 등에 활용할 수 있는 "
    "Word Cloud를 만듭니다. 정확한 빈도는 오른쪽 표에서 함께 확인할 수 있습니다."
)

# 댓글을 다시 분석하지 않고 공통 token_df에서 실제 표기별 빈도를 만듭니다.
surface_token_df = (
    token_df.rename(columns={"표기 변이": "실제 표기"})
    .groupby(
        ["기본형", "실제 표기", "품사 범주", "세부 품사"],
        as_index=False,
        dropna=False,
    )
    .size()
    .rename(columns={"size": "빈도수"})
)

if surface_token_df.empty:
    st.warning("Word Cloud를 만들 수 있는 형태소가 없습니다.")
else:
    cloud_control_col1, cloud_control_col2, cloud_control_col3 = st.columns(3)

    major_values = surface_token_df["품사 범주"].dropna().astype(str).unique().tolist()
    major_options = ["전체"] + ordered_pos_groups(analysis_language, major_values)

    with cloud_control_col1:
        cloud_major_pos = st.selectbox(
            "품사 범주",
            options=major_options,
            key="wordcloud_major_pos",
        )

    if cloud_major_pos == "전체":
        cloud_detail_source = surface_token_df
    else:
        cloud_detail_source = surface_token_df[
            surface_token_df["품사 범주"] == cloud_major_pos
        ]

    detail_values = (
        cloud_detail_source["세부 품사"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    detail_options = ["전체"]

    if cloud_major_pos == "전체":
        detail_options += sorted(detail_values)
    else:
        detail_options += ordered_detailed_pos(
            analysis_language,
            cloud_major_pos,
            detail_values,
        )

    current_cloud_detail = st.session_state.get("wordcloud_detailed_pos", "전체")
    if current_cloud_detail not in detail_options:
        st.session_state["wordcloud_detailed_pos"] = "전체"

    with cloud_control_col2:
        cloud_detailed_pos = st.selectbox(
            "세부 품사",
            options=detail_options,
            key="wordcloud_detailed_pos",
        )

    with cloud_control_col3:
        cloud_unit = st.radio(
            "표시 단위",
            options=["기본형", "실제 표기"],
            horizontal=True,
            key="wordcloud_unit",
            help=(
                "기본형은 활용형과 굴절형을 통합합니다. 실제 표기는 댓글에 나타난 "
                "最高·サイコー·さいこう 같은 형태를 각각 따로 표시합니다."
            ),
        )

    cloud_option_col1, cloud_option_col2, cloud_option_col3, cloud_option_col4 = st.columns(4)

    with cloud_option_col1:
        cloud_min_frequency = st.number_input(
            "최소 빈도",
            min_value=1,
            max_value=1000,
            value=2,
            step=1,
            key="wordcloud_min_frequency",
        )

    with cloud_option_col2:
        cloud_max_words = st.slider(
            "표시할 단어 수",
            min_value=10,
            max_value=200,
            value=60,
            step=10,
            key="wordcloud_max_words",
        )

    with cloud_option_col3:
        cloud_ratio = st.selectbox(
            "이미지 비율",
            options=["가로형 16:9", "정사각형 1:1"],
            key="wordcloud_ratio",
        )

    with cloud_option_col4:
        cloud_transparent = st.checkbox(
            "투명 배경",
            value=False,
            key="wordcloud_transparent",
        )

    cloud_df = surface_token_df.copy()

    if cloud_major_pos != "전체":
        cloud_df = cloud_df[cloud_df["품사 범주"] == cloud_major_pos]

    if cloud_detailed_pos != "전체":
        cloud_df = cloud_df[cloud_df["세부 품사"] == cloud_detailed_pos]

    display_column = "기본형" if cloud_unit == "기본형" else "실제 표기"

    cloud_frequency_df = (
        cloud_df.groupby(display_column, as_index=False, dropna=False)["빈도수"]
        .sum()
        .rename(columns={display_column: "단어"})
    )
    cloud_frequency_df["단어"] = cloud_frequency_df["단어"].astype(str).str.strip()
    cloud_frequency_df = cloud_frequency_df[
        (cloud_frequency_df["단어"] != "")
        & (cloud_frequency_df["빈도수"] >= int(cloud_min_frequency))
    ]
    cloud_frequency_df = cloud_frequency_df.sort_values(
        ["빈도수", "단어"],
        ascending=[False, True],
    ).head(int(cloud_max_words))

    if cloud_frequency_df.empty:
        st.info("현재 조건과 최소 빈도를 만족하는 단어가 없습니다.")
    else:
        font_path = find_wordcloud_font(analysis_language)

        if analysis_language in {"한국어", "일본어"} and font_path is None:
            st.error(
                "한글·일본어를 표시할 수 있는 글꼴을 찾지 못했습니다. "
                "Streamlit Cloud의 packages.txt에 fonts-noto-cjk를 추가해 주세요."
            )
        else:
            if cloud_ratio == "가로형 16:9":
                cloud_width, cloud_height = 1600, 900
            else:
                cloud_width, cloud_height = 1200, 1200

            frequency_dict = {
                str(row["단어"]): int(row["빈도수"])
                for _, row in cloud_frequency_df.iterrows()
            }

            with st.spinner("Word Cloud를 생성하는 중입니다..."):
                cloud, cloud_png = make_wordcloud_png(
                    frequencies=frequency_dict,
                    font_path=font_path,
                    width=cloud_width,
                    height=cloud_height,
                    transparent=cloud_transparent,
                )

            cloud_image_col, cloud_table_col = st.columns([1.65, 1])

            with cloud_image_col:
                st.image(
                    cloud_png,
                    caption=(
                        f"{analysis_language} · {cloud_major_pos} · "
                        f"{cloud_detailed_pos} · {cloud_unit} 기준"
                    ),
                    use_container_width=True,
                )

                st.download_button(
                    "Word Cloud PNG 다운로드",
                    data=cloud_png,
                    file_name=(
                        f"youtube_wordcloud_{analysis_language}_"
                        f"{cloud_major_pos}_{cloud_unit}.png"
                    ),
                    mime="image/png",
                    use_container_width=True,
                )

            with cloud_table_col:
                st.markdown("#### 사용된 단어와 빈도")
                st.metric("표시 단어 수", f"{len(cloud_frequency_df):,}개")
                st.dataframe(
                    cloud_frequency_df[["단어", "빈도수"]],
                    use_container_width=True,
                    hide_index=True,
                    height=min(650, 38 + 35 * len(cloud_frequency_df)),
                    column_config={
                        "단어": st.column_config.TextColumn("단어"),
                        "빈도수": st.column_config.NumberColumn("빈도수", format="%d"),
                    },
                )

            if cloud_unit == "실제 표기":
                st.caption(
                    "실제 표기 기준에서는 대소문자, 한자·가나, 활용형 등의 표면형이 "
                    "서로 다른 단어로 표시됩니다."
                )
            else:
                st.caption(
                    "기본형 기준에서는 분석기가 같은 기본형으로 처리한 활용형·굴절형과 "
                    "표기 변이를 합산합니다."
                )

