import streamlit as st
import random
import uuid
import pandas as pd

# ====== App 基本設定 ======
st.set_page_config(
    page_title="Chem / Element Practice",
    page_icon="📝",
    layout="centered"
)

# ====== CSS：sidebar 保留、畫面貼頂、footer隱藏 ======
st.markdown("""
<style>

/* (A) sidebar保留 */

/* (B) 隱藏主畫面標頭、雲端工具列（fork/share）和 footer */
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer,
div[role="contentinfo"],
div[data-testid="stStatusWidget"],
div[class*="viewerBadge_container"],
div[class*="stActionButtonIcon"],
div[class*="stDeployButton"],
div[data-testid="stDecoration"],
div[data-testid="stMainMenu"],
div[class*="stFloatingActionButton"],
a[class^="css-"][href*="streamlit.io"],
button[kind="header"] {
    display: none !important;
}

/* (C) 最硬核貼頂 */
div[data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
div[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
main.block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
    padding-bottom: 0.9rem !important;
    max-width: 1000px;
}
div[data-testid="stVerticalBlock"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
div[data-testid="stVerticalBlock"] > div:first-child {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* 進度條卡片本體 */
.progress-card {
    margin-top: 0 !important;
    margin-bottom: 0.22rem !important;
}

/* (D) 版面可讀性 */
html, body, [class*="css"]  {
    font-size: 22px !important;
}
h1, h2, h3 {
    line-height: 1.35em !important;
}
h2 {
    font-size: 26px !important;
    margin-top: 0.22em !important;
    margin-bottom: 0.22em !important;
}

/* 單選題區塊靠緊上面標題 */
.stRadio { margin-top: 0 !important; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stRadio"]) {
    margin-top: 0 !important;
}

/* 主要按鈕（送出答案 / 下一題 / 重新開始 / 開始作答） */
.stButton>button{
    height: 44px;
    padding: 0 18px;
    font-size: 20px;
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.2);
}

/* 回饋訊息（答對/答錯） */
.feedback-small {
    font-size: 17px !important;
    line-height: 1.4;
    margin: 6px 0 2px 0;
    display: inline-block;
    padding: 4px 6px;
    border-radius: 6px;
    border: 2px solid transparent;
}
.feedback-correct {
    color: #1a7f37;
    border-color: #1a7f37;
    background-color: #e8f5e9;
    font-weight: 700;
}
.feedback-wrong {
    color: #c62828;
    border-color: #c62828;
    background-color: #ffebee;
    font-weight: 700;
}

/* 模式三輸入框外觀 (如果未來用到手寫) */
.text-input-big input {
    font-size: 24px !important;
    height: 3em !important;
    border-radius: 10px !important;
    border: 1px solid rgba(0,0,0,0.3) !important;
}

</style>
""", unsafe_allow_html=True)


# ===================== 題庫載入（容錯版，這次抓 name / english / symbol） =====================
@st.cache_data
def load_question_bank(xlsx_path="element_app.xlsx"):
    """
    嘗試讀取 Excel 並自動對應三欄：
      name    -> 可能: Name, 中文, 名稱, Chinese, CN
      english -> 可能: English, 英文, Term, 英文名, EN, English term
      symbol  -> 可能: Symbol, 符號, 元素符號, abbrev, 符號Symbol, 符號/代號, symbol(en)

    回傳:
    {
      "ok": bool,
      "error": str,
      "bank": [ { "name":..., "english":..., "symbol":...}, ... ],
      "debug_cols": [...]
    }
    """
    try:
        df = pd.read_excel(xlsx_path)
    except Exception as e:
        return {
            "ok": False,
            "error": f"無法讀取題庫檔案 {xlsx_path} ：{e}",
            "bank": [],
            "debug_cols": []
        }

    def norm(s):
        return str(s).strip().lower()

    cols_norm = {norm(c): c for c in df.columns}

    name_candidates = ["name", "中文", "名稱", "chinese", "cn"]
    eng_candidates  = ["english", "英文", "term", "英文名", "en", "english term"]
    sym_candidates  = ["symbol", "符號", "元素符號", "符號symbol", "abbrev", "代號", "符號/代號"]

    def pick_col(cands):
        for cand in cands:
            if cand in cols_norm:
                return cols_norm[cand]
        return None

    name_col = pick_col(name_candidates)
    eng_col  = pick_col(eng_candidates)
    sym_col  = pick_col(sym_candidates)

    if name_col is None or eng_col is None or sym_col is None:
        return {
            "ok": False,
            "error": (
                "找不到必要欄位。\n"
                f"目前檔案欄位是：{list(df.columns)}\n"
                f"Name欄候選：{name_candidates}\n"
                f"English欄候選：{eng_candidates}\n"
                f"Symbol欄候選：{sym_candidates}\n"
                "請把 Excel 欄位命名成其中一個候選名稱（例如：Name / English / Symbol）。"
            ),
            "bank": [],
            "debug_cols": list(df.columns)
        }

    def clean(x):
        if pd.isna(x):
            return ""
        return str(x).strip()

    bank_list = []
    for _, row in df.iterrows():
        nm = clean(row.get(name_col, ""))
        en = clean(row.get(eng_col, ""))
        sy = clean(row.get(sym_col, ""))
        if nm and en and sy:
            bank_list.append({
                "name": nm,
                "english": en,
                "symbol": sy,
            })

    return {
        "ok": True,
        "error": "",
        "bank": bank_list,
        "debug_cols": list(df.columns)
    }

loaded = load_question_bank()
QUESTION_BANK = loaded["bank"]

if not loaded["ok"] or not QUESTION_BANK:
    st.error("⚠ 題庫讀取失敗或為空，請檢查 Excel 欄位。")
    st.stop()


# ===================== 常數 / 模式名稱 =====================
MAX_ROUNDS = 3
QUESTIONS_PER_ROUND = 10

MODE_1 = "模式一：Name ➜ English"
MODE_2 = "模式二：English ➜ Symbol"
MODE_3 = "模式三：Symbol ➜ English"
MODE_4 = "模式四：混合 (1~3)"

ALL_MODES = [MODE_1, MODE_2, MODE_3, MODE_4]

# 對應：子模式用代碼，方便混合模式逐題紀錄
SUBMODE_NAME_TO_CODE = {
    MODE_1: "name_to_eng",
    MODE_2: "eng_to_sym",
    MODE_3: "sym_to_eng",
}
SUBMODE_LIST_FOR_MIX = ["name_to_eng", "eng_to_sym", "sym_to_eng"]


# ===================== Session State 初始化 & 工具 =====================
def init_game_state():
    """初始化遊戲用的狀態 (不包含 user_name 等資料)"""
    st.session_state.round = 1
    st.session_state.used_pairs = set()             # 用過的 key，減少重複
    st.session_state.cur_round_qidx = []            # 本回合抽到的題庫 index
    st.session_state.cur_idx_in_round = 0           # 當前第幾題 (0-based)
    st.session_state.score_this_round = 0
    st.session_state.submitted = False              # 目前題是否已交
    st.session_state.last_feedback = ""             # HTML feedback
    st.session_state.answer_cache = ""              # 保留輸入（如果之後要文字輸入）
    st.session_state.options_cache = {}             # (qidx, submode) -> options
    st.session_state.submode_per_question = []      # 和 cur_round_qidx 對齊，記錄每題用哪種問法
    st.session_state.records = []                   # (round,prompt,chosen,correct_show,is_correct,opts,submode)

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())


def start_new_round():
    """抽一個新回合的題目清單 & (如果是混合) 同步抽子模式"""
    # 可避免重複的key 我們用 'english' 當唯一 key
    available = [
        i for i, it in enumerate(QUESTION_BANK)
        if it["english"] not in st.session_state.used_pairs
    ]
    if len(available) == 0:
        st.session_state.used_pairs = set()
        available = list(range(len(QUESTION_BANK)))

    if len(available) <= QUESTIONS_PER_ROUND:
        chosen = available[:]
        random.shuffle(chosen)
    else:
        chosen = random.sample(available, QUESTIONS_PER_ROUND)

    st.session_state.cur_round_qidx = chosen
    st.session_state.cur_idx_in_round = 0
    st.session_state.score_this_round = 0
    st.session_state.submitted = False
    st.session_state.last_feedback = ""
    st.session_state.answer_cache = ""
    st.session_state.options_cache = {}

    # 針對每一題決定子模式
    if st.session_state.chosen_mode_label == MODE_4:
        st.session_state.submode_per_question = [
            random.choice(SUBMODE_LIST_FOR_MIX) for _ in chosen
        ]
    else:
        # 非混合 -> 全部同一種子模式
        code = SUBMODE_NAME_TO_CODE[st.session_state.chosen_mode_label]
        st.session_state.submode_per_question = [code for _ in chosen]


def ensure_state_ready():
    needed_keys = [
        "mode_locked",
        "chosen_mode_label",
        "round",
        "used_pairs",
        "cur_round_qidx",
        "cur_idx_in_round",
        "score_this_round",
        "submitted",
        "last_feedback",
        "answer_cache",
        "options_cache",
        "session_id",
        "user_name",
        "user_class",
        "user_seat",
        "submode_per_question",
        "records"
    ]
    missing = any(k not in st.session_state for k in needed_keys)

    if missing:
        if "mode_locked" not in st.session_state:
            st.session_state.mode_locked = False
        if "chosen_mode_label" not in st.session_state:
            st.session_state.chosen_mode_label = None

        if "user_name" not in st.session_state:
            st.session_state.user_name = ""
        if "user_class" not in st.session_state:
            st.session_state.user_class = ""
        if "user_seat" not in st.session_state:
            st.session_state.user_seat = ""

        init_game_state()

    # 如果 round 還有值、但題目列表是空的，補抽
    if st.session_state.mode_locked and st.session_state.round and not st.session_state.cur_round_qidx:
        start_new_round()


ensure_state_ready()


# ===================== 產生選項 =====================
def get_options_for_q(qidx, submode_code):
    """
    submode_code:
      "name_to_eng":     題目顯示 Name,   選 English
      "eng_to_sym":      題目顯示 English,選 Symbol
      "sym_to_eng":      題目顯示 Symbol, 選 English

    回傳 dict:
    {
      "display": [...兩個選項字串...],
    }
    """
    key = (qidx, submode_code)
    if key in st.session_state.options_cache:
        return st.session_state.options_cache[key]

    item = QUESTION_BANK[qidx]
    correct_name   = item["name"].strip()
    correct_eng    = item["english"].strip()
    correct_symbol = item["symbol"].strip()

    if submode_code == "name_to_eng":
        # 正解 = English，干擾 = 另一個 English
        pool = [
            it["english"].strip()
            for it in QUESTION_BANK
            if it["english"].strip().lower() != correct_eng.lower()
        ]
        distractor = random.choice(pool) if pool else "???"
        opts = [correct_eng, distractor]

    elif submode_code == "eng_to_sym":
        # 正解 = Symbol，干擾 = 另一個 Symbol
        pool = [
            it["symbol"].strip()
            for it in QUESTION_BANK
            if it["symbol"].strip().lower() != correct_symbol.lower()
        ]
        distractor = random.choice(pool) if pool else "???"
        opts = [correct_symbol, distractor]

    else:  # "sym_to_eng"
        # 正解 = English，干擾 = 另一個 English
        pool = [
            it["english"].strip()
            for it in QUESTION_BANK
            if it["english"].strip().lower() != correct_eng.lower()
        ]
        distractor = random.choice(pool) if pool else "???"
        opts = [correct_eng, distractor]

    random.shuffle(opts)
    payload = {"display": opts[:]}

    st.session_state.options_cache[key] = payload
    return payload


# ===================== 進度條卡 =====================
def render_top_card():
    r = st.session_state.round
    i = st.session_state.cur_idx_in_round + 1
    n = len(st.session_state.cur_round_qidx)
    percent = int(i / n * 100) if n else 0

    st.markdown(
        f"""
        <div class="progress-card"
             style='background-color:#f5f5f5;
                    padding:9px 14px;
                    border-radius:12px;'>
            <div style='display:flex;
                        align-items:center;
                        justify-content:space-between;
                        margin-bottom:4px;'>
                <div style='font-size:18px;'>
                    🎯 第 {r} 回合｜進度：{i} / {n}
                </div>
                <div style='font-size:16px; color:#555;'>{percent}%</div>
            </div>
            <progress value='{i}'
                      max='{n if n else 1}'
                      style='width:100%; height:14px;'></progress>
        </div>
        """,
        unsafe_allow_html=True
    )


# ===================== 題目顯示 =====================
def render_question():
    cur_pos = st.session_state.cur_idx_in_round
    qidx = st.session_state.cur_round_qidx[cur_pos]
    q = QUESTION_BANK[qidx]

    submode_code = st.session_state.submode_per_question[cur_pos]

    # 根據 submode_code 決定題目文字與正確答案欄位
    if submode_code == "name_to_eng":
        # 題幹：給 Name
        prompt_txt = q["name"].strip()
        question_prompt = f'「{prompt_txt}」的正確英文是？'
    elif submode_code == "eng_to_sym":
        # 題幹：給 English
        prompt_txt = q["english"].strip()
        question_prompt = f'「{prompt_txt}」對應的正確符號(Symbol)是？'
    else:  # "sym_to_eng"
        # 題幹：給 Symbol
        prompt_txt = q["symbol"].strip()
        question_prompt = f'符號「{prompt_txt}」的正確英文名稱是？'

    st.markdown(
        f"<h2>Q{cur_pos + 1}. {question_prompt}</h2>",
        unsafe_allow_html=True
    )

    payload = get_options_for_q(qidx, submode_code)
    options_disp = payload["display"]
    if not options_disp:
        st.info("No options to select.")
        user_choice_disp = None
    else:
        user_choice_disp = st.radio(
            "",
            options_disp,
            key=f"mc_{qidx}",
            label_visibility="collapsed"
        )

    # 回傳本題資料
    return qidx, q, submode_code, ("mc", user_choice_disp, payload)


# ===================== 答案提交 / 下一題邏輯 =====================
def handle_action(qidx, q, submode_code, user_input):
    correct_name   = q["name"].strip()
    correct_eng    = q["english"].strip()
    correct_symbol = q["symbol"].strip()

    ui_type, data, payload = user_input

    # 決定正解字串
    if submode_code == "name_to_eng":
        correct_answer = correct_eng
    elif submode_code == "eng_to_sym":
        correct_answer = correct_symbol
    else:
        correct_answer = correct_eng  # sym_to_eng

    # 使用者的選項
    if data is None:
        st.warning("請先選擇一個選項。")
        return
    chosen_label = data.strip()

    # 判斷對錯 (大小寫寬鬆)
    is_correct = (chosen_label.lower() == correct_answer.lower())

    # 第一次按：送出答案
    if not st.session_state.submitted:
        st.session_state.submitted = True

        # 紀錄
        st.session_state.records.append((
            st.session_state.round,     # 第幾回合
            prompt_for_record(q, submode_code),  # 題幹顯示給紀錄
            chosen_label,               # 學生選的
            correct_answer,             # 正確答案
            is_correct,                 # 對錯
            (payload["display"] if (payload and "display" in payload) else None),
            submode_code                # 紀錄出題型態
        ))

        # 產生回饋
        if is_correct:
            st.session_state.last_feedback = (
                "<div class='feedback-small feedback-correct'>✅ 回答正確</div>"
            )
            st.session_state.score_this_round += 1
        else:
            # 依 submode_code 不同，回饋要同時顯示對應的對照資訊
            if submode_code == "name_to_eng":
                # Name -> English
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. 正確答案："
                    f"{correct_eng} （Symbol: {correct_symbol}, Name: {correct_name}）</div>"
                )
            elif submode_code == "eng_to_sym":
                # English -> Symbol
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. 正確符號："
                    f"{correct_symbol} （{correct_eng} / {correct_name}）</div>"
                )
            else:
                # Symbol -> English
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. 正確英文："
                    f"{correct_eng} （Symbol: {correct_symbol}, Name: {correct_name}）</div>"
                )

        st.rerun()
        return

    # 第二次按：下一題
    else:
        # 把這題的英文單字標記成已用
        st.session_state.used_pairs.add(correct_eng)

        # 進下一題
        st.session_state.cur_idx_in_round += 1
        st.session_state.submitted = False
        st.session_state.last_feedback = ""
        st.session_state.answer_cache = ""

        # 回合結束檢查
        if st.session_state.cur_idx_in_round >= len(st.session_state.cur_round_qidx):
            full_score = (
                st.session_state.score_this_round
                == len(st.session_state.cur_round_qidx)
            )
            has_more_rounds = (st.session_state.round < MAX_ROUNDS)

            if full_score and has_more_rounds:
                st.session_state.round += 1
                start_new_round()
            else:
                # 遊戲結束
                st.session_state.round = None

        st.rerun()
        return


def prompt_for_record(q, submode_code):
    """
    給 records 用的「題幹顯示文字」
    """
    if submode_code == "name_to_eng":
        return q["name"].strip()
    elif submode_code == "eng_to_sym":
        return q["english"].strip()
    else:
        return q["symbol"].strip()


# ===================== 畫面一：模式選擇頁 =====================
def render_mode_select_page():
    st.markdown("## 選擇練習模式")
    st.write("請選一種模式後開始作答：")

    chosen = st.radio(
        "練習模式",
        ALL_MODES,
        index=0,
        key="mode_pick_for_start"
    )

    st.session_state.user_class = st.text_input(
        "班級", st.session_state.get("user_class", "")
    )
    st.session_state.user_seat = st.text_input(
        "座號", st.session_state.get("user_seat", "")
    )

    if st.button("開始作答 ▶"):
        st.session_state.chosen_mode_label = chosen
        st.session_state.mode_locked = True

        init_game_state()
        # chosen_mode_label 會在 start_new_round() 被參考
        st.session_state.chosen_mode_label = chosen
        start_new_round()

        st.rerun()


# ===================== 畫面二：作答頁 =====================
def render_quiz_page():
    # 側邊欄
    with st.sidebar:
        st.markdown("### 你的資訊")
        st.text_input(
            "姓名",
            st.session_state.get("user_name", ""),
            key="user_name"
        )
        st.text_input(
            "班級",
            st.session_state.get("user_class", ""),
            key="user_class"
        )
        st.text_input(
            "座號",
            st.session_state.get("user_seat", ""),
            key="user_seat"
        )

        st.markdown("---")
        st.write("模式已鎖定：")
        st.write(st.session_state.chosen_mode_label)

        if st.button("🔄 重新開始（重新選模式）"):
            st.session_state.mode_locked = False
            st.session_state.chosen_mode_label = None
            init_game_state()
            st.rerun()

    # 主內容
    if st.session_state.round:
        # 進行中
        render_top_card()
        qidx, q, submode_code, user_input = render_question()

        # 如果已經送出答案，顯示回饋
        if st.session_state.submitted and st.session_state.last_feedback:
            st.markdown(st.session_state.last_feedback, unsafe_allow_html=True)

        # 主按鈕
        action_label = "下一題" if st.session_state.submitted else "送出答案"
        if st.button(action_label, key="action_btn"):
            handle_action(qidx, q, submode_code, user_input)

        # 題目提交後複習區
        if st.session_state.submitted and st.session_state.records:
            last = st.session_state.records[-1]
            # last = (round,prompt,chosen_label,correct_answer,is_correct,opts,submode_code)
            _, _, _, correct_ans, _, opts_disp, last_submode = last

            st.markdown("---")
            if last_submode == "name_to_eng":
                # 提一下 symbol/中文 方便複習
                st.markdown(
                    f"**正確英文：{q['english'].strip()}** "
                    f"(Symbol: {q['symbol'].strip()}, Name: {q['name'].strip()})"
                )
            elif last_submode == "eng_to_sym":
                st.markdown(
                    f"**正確符號：{q['symbol'].strip()}** "
                    f"({q['english'].strip()} / {q['name'].strip()})"
                )
            else:  # sym_to_eng
                st.markdown(
                    f"**正確英文：{q['english'].strip()}** "
                    f"(Symbol: {q['symbol'].strip()}, Name: {q['name'].strip()})"
                )

            if opts_disp:
                st.markdown("**本題兩個選項：**")
                # 我們希望把兩個選項都轉成「English(Symbol / Name)」這種雙語/雙資訊
                # 但因為 opts_disp 可能是 symbol 或 english，需要找回原物件
                nice_pairs = []
                for opt in opts_disp:
                    opt_clean = opt.strip().lower()
                    match_item = None
                    for it in QUESTION_BANK:
                        if (it["english"].strip().lower() == opt_clean or
                            it["symbol"].strip().lower() == opt_clean or
                            it["name"].strip().lower() == opt_clean):
                            match_item = it
                            break
                    if match_item:
                        nice_pairs.append(
                            f"{match_item['english'].strip()} "
                            f"({match_item['symbol'].strip()} / {match_item['name'].strip()})"
                        )
                    else:
                        nice_pairs.append(opt.strip())
                st.markdown("、".join(nice_pairs))

    else:
        # 回合都打完
        total_answered = len(st.session_state.records)
        total_correct = sum(1 for rec in st.session_state.records if rec[4])
        acc = (total_correct / total_answered * 100) if total_answered else 0.0

        st.subheader("📊 總結")
        st.markdown(
            f"<h3>Total Answered: {total_answered}</h3>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<h3>Total Correct: {total_correct}</h3>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<h3>Accuracy: {acc:.1f}%</h3>",
            unsafe_allow_html=True
        )

        if st.button("🔄 再玩一次（同模式）"):
            init_game_state()
            start_new_round()
            st.rerun()

        if st.button("🧪 選別的模式"):
            st.session_state.mode_locked = False
            st.session_state.chosen_mode_label = None
            init_game_state()
            st.rerun()


# ===================== 頁面路由 =====================
if not st.session_state.mode_locked:
    render_mode_select_page()
else:
    render_quiz_page()
