# app.py
import streamlit as st
import pandas as pd
import numpy as np

# ───────── 設定 ─────────
CHAR_COL = "character"
EQUIP_COL = "cart"
ATTRS = ["topspeed", "acceleration", "weight", "handling"]
# 属性の日本語表示名
ATTR_NAMES_JP = {
    "topspeed": "スピード",
    "acceleration": "かそく",
    "weight": "おもさ",
    "handling": "まがりやすさ"
}

# ──────────────────────

# ───────── ステータス分解 ─────────
@st.cache_data
def solve_all_attributes(totals: pd.DataFrame, attrs: list[str]):
    chars = totals[CHAR_COL].unique().tolist()
    equips = totals[EQUIP_COL].unique().tolist()
    nC, nE = len(chars), len(equips)

    results = {}
    for attr in attrs:
        rows, b = [], []
        for _, row in totals.iterrows():
            c = chars.index(row[CHAR_COL])
            e = equips.index(row[EQUIP_COL])
            vec = [0] * (nC + nE)
            vec[c] = 1
            vec[nC + e] = 1
            rows.append(vec)
            b.append(row[attr])
        # 固定基準
        vec = [0] * (nC + nE)
        vec[0] = 1
        rows.append(vec)
        b.append(0.0)

        A = np.array(rows, float)
        x, *_ = np.linalg.lstsq(A, b, rcond=None)
        results[attr] = {
            "char": pd.Series(x[:nC], index=chars),
            "equip": pd.Series(x[nC:], index=equips)
        }
    return results
# ──────────────────────────────────────────

# ───────── ファイル読み込み ─────────
st.title("マリオカートワールド カスタム計算機")
totals = pd.read_csv("totals.csv")
char_info = pd.read_csv("characters.csv").set_index(CHAR_COL)
equip_info = pd.read_csv("carts.csv").set_index(EQUIP_COL)
results = solve_all_attributes(totals, ATTRS)
# ──────────────────────────────

# ───────── メニュー選択 ─────────
tab1, tab2 = st.tabs(["▶ キャラ＋カートを選ぶ", " 目標ステータスから探す"])

with tab1:
    st.header("① キャラ＋カートを選んでステータス表示")

    # ── 1. 「ID ⇒ 表示名」対応辞書を作成 ──
    # characters.csv に 'name' 列がある前提
    char_display = {cid: char_info.loc[cid, "name"] for cid in char_info.index}
    cart_display = {eid: equip_info.loc[eid, "name"] for eid in equip_info.index}

    # ── 2. selectbox で「表示は名前、戻り値はID」──
    # 読み仮名ベースで五十音順にソート
    sorted_char_ids = sorted(
    char_display.keys(),
    key=lambda k: char_info.loc[k, "yomi"]
)
    char = st.selectbox(
    "キャラクター",
    options=sorted_char_ids,
    format_func=lambda x: char_display[x]
)

    sorted_cart_ids = sorted(
    cart_display.keys(),
    key=lambda k: equip_info.loc[k, "yomi"]
)
    cart = st.selectbox(
    "カート",
    options=sorted_cart_ids,
    format_func=lambda x: cart_display[x]
)

    # ── 3. 合成ステータス表示 ──
    st.subheader("合計ステータス")
    for attr in ATTRS:
        val = results[attr]["char"][char] + results[attr]["equip"][cart]
        st.metric(ATTR_NAMES_JP[attr], f"{val:.1f}")

    # ── 4. キャラ・カート詳細 ──
    st.subheader("キャラ情報")
    st.markdown(f"""
    **名前**：{char_info.loc[char, 'name']}  
    **備考**：{char_info.loc[char, 'note']}
    """)

    st.subheader("カート情報")
    st.markdown(f"""
    **名前** : {equip_info.loc[cart, 'name']}  
    **備考** : {equip_info.loc[cart, 'note2']}
    """) 

with tab2:
    st.header("② 目標ステータスに近い組み合わせ検索")

    # --- 目標値 & 重み 入力エリアを 2 列に並べる ---
    col_goal, col_w = st.columns(2, gap="medium")

    goal = {}
    weight = {}
    with col_goal:
        st.subheader(" 目標値")
        for attr in ATTRS:
            goal[attr] = st.slider(ATTR_NAMES_JP[attr], 0.0, 4.0, 2.0, 0.1, key=f"goal_{attr}")

    with col_w:
        st.subheader(" 重み (重要度)")
        for attr in ATTRS:
            weight[attr] = st.slider(ATTR_NAMES_JP[attr], 0.0, 10.0, 1.0, 0.1, key=f"w_{attr}",
                                     help="0=無視, 大きいほど優先")

    st.markdown("---")
    top_n = st.number_input("上位いくつ表示する？", 1, 50, 25, 1)

# --- 距離（重み付きユークリッド）を計算 ---
rows = []
for cid in results[ATTRS[0]]["char"].index:
    for eid in results[ATTRS[0]]["equip"].index:
        entry = {
            "キャラ": char_info.loc[cid, "name"],     # ←名前列
            "カート": equip_info.loc[eid, "name"]
        }
        dist2 = 0
        for attr in ATTRS:
            val = results[attr]["char"][cid] + results[attr]["equip"][eid]
            entry[attr] = round(val, 2)
            dist2 += weight[attr] * (val - goal[attr])**2
        entry["score"] = round(dist2**0.5, 3)
        rows.append(entry)

df = (pd.DataFrame(rows)
      .sort_values("score")
      .head(int(top_n))
      .reset_index(drop=True))

st.subheader(f"🔎 結果 TOP{top_n}")
st.dataframe(
    df.style.background_gradient(subset=["score"], cmap="Greens_r")
             .format("{:.2f}", subset=ATTRS + ["score"]),
    use_container_width=True
)
st.write("作者:meat29")
st.markdown(
    '<p style="text-align: right;">作者:<a haef="https://x.com/meat29">meat29</a><br>何か不都合があれば削除します。<br>LastUpDate:2025/06/29</p>',
    unsafe_allow_html=True
)

    