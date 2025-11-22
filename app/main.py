#!/usr/bin/env python3
"""
金管會智能問答系統 - Streamlit 部署版本

支援三種資料來源：
- 裁罰案件
- 法令函釋
- 重要公告
"""

import streamlit as st
import os
import time
import json
from typing import List, Dict, Any
from pathlib import Path

# 頁面配置
st.set_page_config(
    page_title="金管會智能問答",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Store 配置
STORES = {
    'penalties': {
        'name': 'fsc-penalties-plaintext',
        'store_id': 'fileSearchStores/fscpenaltiesplaintext-4f87t5uexgui',
        'display_name': '裁罰案件',
        'icon': '⚖️',
        'description': '490 筆金融機構裁罰案件 (2012-2025)',
        'count': 490,
    },
    'law_interpretations': {
        'name': 'fsc-law-interpretations',
        'store_id': 'fileSearchStores/fsclawinterpretations-zz5pwrly06hz',
        'display_name': '法令函釋',
        'icon': '📜',
        'description': '法規解釋、修正說明、條文對照',
        'count': 2872,
    },
    'announcements': {
        'name': 'fsc-announcements',
        'store_id': 'fileSearchStores/fscannouncements-o94q0kmo2zxb',
        'display_name': '重要公告',
        'icon': '📢',
        'description': '政策公告、法規修正公告',
        'count': 1642,
    },
}

# 載入 Mapping 檔案
def load_mappings():
    """
    載入所有資料類型的 gemini_id_mapping 和 file_mapping 檔案
    用於將 Gemini 回傳的 file ID 轉換為可讀的顯示名稱
    """
    data_path = Path(__file__).parent.parent / "data"

    gemini_id_mapping = {}  # gemini_short_id → doc_id
    file_mapping = {}       # doc_id → info

    try:
        # === 載入裁罰案件 (舊格式) ===
        penalties_path = data_path / "penalties"

        # gemini_id_mapping.json: {files/xxx: doc_id}
        gemini_mapping_path = penalties_path / "gemini_id_mapping.json"
        if gemini_mapping_path.exists():
            with open(gemini_mapping_path, 'r', encoding='utf-8') as f:
                raw_mapping = json.load(f)
                for full_id, doc_id in raw_mapping.items():
                    short_id = full_id.replace('files/', '')
                    gemini_id_mapping[short_id] = doc_id

        # file_mapping.json: {doc_id: info}
        file_mapping_path = penalties_path / "file_mapping.json"
        if file_mapping_path.exists():
            with open(file_mapping_path, 'r', encoding='utf-8') as f:
                file_mapping.update(json.load(f))

        # === 載入法令函釋 ===
        law_path = data_path / "law_interpretations"
        law_gemini_path = law_path / "gemini_id_mapping_new.json"
        if law_gemini_path.exists():
            with open(law_gemini_path, 'r', encoding='utf-8') as f:
                raw_mapping = json.load(f)
                for doc_id, info in raw_mapping.items():
                    gemini_file_id = info.get('gemini_file_id', '')
                    if gemini_file_id:
                        short_id = gemini_file_id.replace('files/', '')
                        gemini_id_mapping[short_id] = doc_id
                    file_mapping[doc_id] = {
                        'display_name': info.get('display_name', ''),
                        'date': info.get('date', ''),
                        'source': info.get('source', ''),
                        'category': info.get('category', ''),
                        'original_url': info.get('original_url', ''),
                    }

        # === 載入重要公告 ===
        ann_path = data_path / "announcements"
        ann_gemini_path = ann_path / "gemini_id_mapping_new.json"
        if ann_gemini_path.exists():
            with open(ann_gemini_path, 'r', encoding='utf-8') as f:
                raw_mapping = json.load(f)
                for doc_id, info in raw_mapping.items():
                    gemini_file_id = info.get('gemini_file_id', '')
                    if gemini_file_id:
                        short_id = gemini_file_id.replace('files/', '')
                        gemini_id_mapping[short_id] = doc_id
                    file_mapping[doc_id] = {
                        'display_name': info.get('display_name', ''),
                        'date': info.get('date', ''),
                        'source': info.get('source', ''),
                        'category': info.get('category', ''),
                        'original_url': info.get('original_url', ''),
                    }

    except Exception as e:
        st.warning(f"載入 mapping 檔案時發生錯誤: {e}")

    return gemini_id_mapping, file_mapping

# 全域 Mapping (載入一次)
GEMINI_ID_MAPPING, FILE_MAPPING = load_mappings()


def resolve_source_display_name(raw_id: str) -> tuple:
    """
    將 Gemini 回傳的 file ID 解析為可讀的顯示名稱

    回傳: (display_name, source_type, date, original_url)
    """
    # 嘗試從 mapping 查詢
    doc_id = GEMINI_ID_MAPPING.get(raw_id, '')

    if doc_id and doc_id in FILE_MAPPING:
        info = FILE_MAPPING[doc_id]
        display_name = info.get('display_name', '')
        date = info.get('date', '未知日期')
        source = info.get('source', '')
        original_url = info.get('original_url', '')

        # 判斷來源類型
        if doc_id.startswith('fsc_pen'):
            source_type = "裁罰案件"
            icon = "⚖️"
        elif doc_id.startswith('fsc_law'):
            source_type = "法令函釋"
            icon = "📜"
        elif doc_id.startswith('fsc_unk') or doc_id.startswith('fsc_ann'):
            source_type = "重要公告"
            icon = "📢"
        else:
            source_type = "未知"
            icon = "📄"

        # 來源單位中文化
        source_map = {
            'insurance_bureau': '保險局',
            'securities_bureau': '證期局',
            'bank_bureau': '銀行局',
            'fsc': '金管會',
        }
        source_display = source_map.get(source, source)

        # 格式化顯示名稱
        if display_name:
            # 裁罰案件格式: "2025-09-25_保險局_全球人壽"
            # 新格式: "2025-11-14_insurance_bureau_ann_amendment_fsc_unk_..."
            parts = display_name.split('_')
            if doc_id.startswith('fsc_pen') and len(parts) >= 3:
                # 裁罰: 日期_來源_機構名稱
                return f"{icon} {parts[0]}_{parts[2]}", source_type, date, original_url
            elif len(parts) >= 2:
                # 法令函釋/公告: 日期_來源
                return f"{icon} {date}_{source_display}", source_type, date, original_url

        return f"{icon} {source_type}_{date}", source_type, date, original_url

    # 如果 mapping 找不到，嘗試從原始名稱解析
    return f"📄 {format_source_display_name(raw_id)}", "未知", "未知日期", ""


# 範例問題
EXAMPLE_QUESTIONS = [
    "違反金控法利害關係人規定會受到什麼處罰？",
    "請問在證券因為專業投資人資格審核的裁罰有哪些？",
    "辦理共同行銷被裁罰的案例有哪些？",
    "金管會對創投公司的裁罰有哪些？",
    "證券商遭主管機關裁罰「警告」處分，有哪些業務會受限制？",
    "內線交易有罪判決所認定重大訊息成立的時點",
]


def get_system_prompt(selected_stores: List[str]) -> str:
    """
    根據選取的 Store 組合產生系統提示
    """
    base_prompt = """你是專業的金融法規顧問。請根據參考資料回答問題。

回答時必須：
1. 明確引用來源文件（檔案名稱、日期）
2. 如果資料中沒有相關資訊，請誠實說明
3. 使用繁體中文回答
4. 保持專業、客觀的態度
"""

    # 根據選取的 Store 加入特定指引
    specific_guidelines = []

    if 'penalties' in selected_stores:
        specific_guidelines.append("""
【裁罰案件指引】
- 列舉具體案例與裁罰內容
- 說明受罰機構、罰款金額、違規行為
- 引用相關法律依據""")

    if 'law_interpretations' in selected_stores:
        specific_guidelines.append("""
【法令函釋指引】
- 解釋法規的具體含義
- 列出修正前後的差異（如有）
- 引用發文字號""")

    if 'announcements' in selected_stores:
        specific_guidelines.append("""
【重要公告指引】
- 說明公告的主要內容
- 列出生效日期（如有）
- 引用公告文號""")

    # 組合提示
    if specific_guidelines:
        return base_prompt + "\n" + "\n".join(specific_guidelines)
    return base_prompt


def query_gemini(question: str, selected_stores: List[str], api_key: str) -> Dict[str, Any]:
    """
    使用 Gemini File Search 執行查詢
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # 取得選取的 Store IDs
    store_ids = [STORES[s]['store_id'] for s in selected_stores if s in STORES]

    if not store_ids:
        return {
            'answer': '請至少選擇一個資料來源',
            'sources': [],
            'error': True
        }

    # 取得系統提示
    system_prompt = get_system_prompt(selected_stores)

    start_time = time.time()

    try:
        # 執行查詢
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=question,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=store_ids
                        )
                    )
                ],
                temperature=0.1,
                max_output_tokens=2000,
                system_instruction=system_prompt
            )
        )

        latency = time.time() - start_time

        # 提取答案
        answer = response.text if hasattr(response, 'text') else str(response)

        # 提取來源
        sources = extract_sources(response)

        return {
            'answer': answer,
            'sources': sources,
            'latency': latency,
            'error': False
        }

    except Exception as e:
        return {
            'answer': f'查詢失敗: {str(e)}',
            'sources': [],
            'error': True
        }


def format_source_display_name(raw_name: str) -> str:
    """
    將原始檔案名稱格式化為易讀的顯示名稱

    原始格式範例：
    - 法令函釋: 2006-03-03_securities_bureau_law_amendment_fsc_law_201406240001
    - 重要公告: 2019-01-02_insurance_bureau_ann_amendment_fsc_unk_20190102_1648
    - 裁罰案件: 2025-09-25_insurance_bureau_penalty_fsc_pen_20250925_0001

    輸出格式：
    - 法令函釋_2006-03-03
    - 重要公告_2019-01-02
    - 裁罰案件_2025-09-25
    """
    if not raw_name:
        return "未知文件"

    # 判斷來源類型
    source_type = "未知"
    if 'fsc_law' in raw_name or 'law_' in raw_name:
        source_type = "法令函釋"
    elif 'fsc_unk' in raw_name or 'ann_' in raw_name:
        source_type = "重要公告"
    elif 'fsc_pen' in raw_name or 'penalty' in raw_name:
        source_type = "裁罰案件"

    # 提取日期（格式：YYYY-MM-DD）
    date = "未知日期"
    parts = raw_name.split('_')
    if parts and len(parts[0]) == 10 and '-' in parts[0]:
        date = parts[0]

    return f"{source_type}_{date}"


def extract_sources(response) -> List[Dict[str, Any]]:
    """
    從 Gemini 回應中提取來源
    """
    sources = []

    try:
        if hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]

            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                metadata = candidate.grounding_metadata

                if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                    for i, chunk in enumerate(metadata.grounding_chunks):
                        if hasattr(chunk, 'retrieved_context'):
                            context = chunk.retrieved_context

                            # 提取原始檔名/ID
                            raw_id = ""
                            if hasattr(context, 'title') and context.title:
                                raw_id = context.title
                            elif hasattr(context, 'uri') and context.uri:
                                raw_id = context.uri.split('/')[-1]

                            # 使用 mapping 解析顯示名稱
                            display_name, source_type, date, original_url = resolve_source_display_name(raw_id)

                            snippet = ""
                            if hasattr(context, 'text') and context.text:
                                snippet = context.text[:500]

                            score = 1.0
                            if hasattr(chunk, 'score'):
                                score = float(chunk.score)

                            sources.append({
                                'filename': display_name,
                                'raw_id': raw_id,
                                'source_type': source_type,
                                'date': date,
                                'snippet': snippet,
                                'score': score,
                                'original_url': original_url,
                            })

    except Exception as e:
        st.warning(f"提取來源時發生錯誤: {e}")

    return sources


def render_sidebar():
    """渲染側邊欄"""
    with st.sidebar:
        st.header("📊 資料來源")

        # Store 選擇（多選）
        selected_stores = []
        for key, store in STORES.items():
            checked = st.checkbox(
                f"{store['icon']} {store['display_name']}",
                value=(key == 'penalties'),  # 預設選取裁罰案件
                key=f"store_{key}",
                help=store['description']
            )
            if checked:
                selected_stores.append(key)

        st.markdown("---")

        # 顯示選取的資料統計
        if selected_stores:
            total_docs = sum(STORES[s]['count'] for s in selected_stores)
            st.metric("📚 文件總數", f"{total_docs:,}")

            with st.expander("ℹ️ 資料說明", expanded=False):
                for key in selected_stores:
                    store = STORES[key]
                    st.caption(f"{store['icon']} **{store['display_name']}**")
                    st.caption(f"  {store['description']}")
                    st.caption(f"  共 {store['count']:,} 筆")
        else:
            st.warning("請至少選擇一個資料來源")

        st.markdown("---")

        # 使用說明
        with st.expander("💡 使用說明", expanded=False):
            st.markdown("""
            **如何使用：**
            1. 在左側選擇要查詢的資料來源
            2. 輸入您的問題
            3. 點擊「查詢」按鈕
            4. 查看 AI 生成的答案和參考來源

            **資料來源說明：**
            - **裁罰案件**：金融機構違規裁罰記錄
            - **法令函釋**：法規解釋和修正說明
            - **重要公告**：金管會政策公告
            """)

        st.markdown("---")
        st.caption("🤖 AI 智能問答系統")
        st.caption("⚠️ 本系統僅供參考")

    return selected_stores


def main():
    """主程式"""
    # 取得 API Key
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("請設定 GEMINI_API_KEY")
        st.stop()

    # 渲染側邊欄
    selected_stores = render_sidebar()

    # 主標題
    st.title("🏛️ 金管會智能問答")
    st.caption("💡 本系統為展示用，如遇畫面無反應，請重新整理頁面")

    # 問題輸入
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""

    question = st.text_area(
        "請輸入您的問題：",
        value=st.session_state.current_question,
        placeholder="例如：哪些銀行因為理專挪用客戶款項被裁罰？",
        height=100
    )

    # 更新 session state
    if question != st.session_state.current_question:
        st.session_state.current_question = question

    # 按鈕列
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        submit_button = st.button("🔍 查詢", type="primary", use_container_width=True)

    with col2:
        if st.button("🗑️ 清除", use_container_width=True):
            st.session_state.current_question = ""
            st.rerun()

    # 處理查詢
    if submit_button and question:
        if not selected_stores:
            st.error("請至少選擇一個資料來源")
        else:
            with st.spinner("🔍 AI 查詢中..."):
                result = query_gemini(question, selected_stores, api_key)

            if result['error']:
                st.error(result['answer'])
            else:
                # 顯示結果
                st.success("✅ 查詢完成")

                # 指標欄（使用較小字體）
                stores_text = ", ".join([STORES[s]['display_name'] for s in selected_stores])
                st.caption(f"⏱️ 回應時間: {result['latency']:.2f} 秒　｜　📚 來源數量: {len(result['sources'])} 筆　｜　📂 查詢範圍: {stores_text}")

                st.markdown("---")

                # 答案
                st.subheader("📝 答案")
                st.markdown(result['answer'])

                st.markdown("---")

                # 來源（按類型分組，各組按時間排序）
                if result['sources']:
                    st.subheader(f"📚 參考來源 ({len(result['sources'])} 筆)")

                    # 按類型分組
                    penalties = [s for s in result['sources'] if s.get('source_type') == "裁罰案件"]
                    law_interps = [s for s in result['sources'] if s.get('source_type') == "法令函釋"]
                    announcements = [s for s in result['sources'] if s.get('source_type') == "重要公告"]
                    others = [s for s in result['sources'] if s.get('source_type') not in ["裁罰案件", "法令函釋", "重要公告"]]

                    # 各組按日期排序（最新到最舊）
                    for group in [penalties, law_interps, announcements, others]:
                        group.sort(key=lambda x: x.get('date', ''), reverse=True)

                    # 依序顯示：裁罰 → 函釋 → 公告 → 其他
                    type_config = [
                        ("⚖️", "裁罰案件", penalties),
                        ("📜", "法令函釋", law_interps),
                        ("📢", "重要公告", announcements),
                        ("📄", "其他", others),
                    ]

                    for icon, type_name, sources_list in type_config:
                        if not sources_list:
                            continue

                        st.caption(f"{icon} {type_name} ({len(sources_list)} 筆)")
                        for source in sources_list:
                            with st.expander(
                                f"{icon} {source['filename']}",
                                expanded=False
                            ):
                                st.markdown(f"**相關內容：**")
                                st.markdown(f"> {source['snippet'][:300]}...")

                                if source['score'] < 1.0:
                                    st.caption(f"相似度: {source['score']:.2%}")

                                # 顯示原始網頁連結
                                if source.get('original_url'):
                                    st.markdown(f"[🔗 查看原始網頁]({source['original_url']})")
                else:
                    # sources=0 自動重試
                    st.warning("⚠️ 未找到參考來源，正在重試...")
                    with st.spinner("重新查詢中..."):
                        result2 = query_gemini(question, selected_stores, api_key)

                    if result2['sources']:
                        st.success("✅ 重試成功")
                        st.markdown(result2['answer'])

                        # 按類型分組並排序
                        penalties2 = sorted([s for s in result2['sources'] if s.get('source_type') == "裁罰案件"], key=lambda x: x.get('date', ''), reverse=True)
                        law_interps2 = sorted([s for s in result2['sources'] if s.get('source_type') == "法令函釋"], key=lambda x: x.get('date', ''), reverse=True)
                        announcements2 = sorted([s for s in result2['sources'] if s.get('source_type') == "重要公告"], key=lambda x: x.get('date', ''), reverse=True)
                        others2 = sorted([s for s in result2['sources'] if s.get('source_type') not in ["裁罰案件", "法令函釋", "重要公告"]], key=lambda x: x.get('date', ''), reverse=True)

                        for icon, type_name, sources_list in [("⚖️", "裁罰案件", penalties2), ("📜", "法令函釋", law_interps2), ("📢", "重要公告", announcements2), ("📄", "其他", others2)]:
                            if not sources_list:
                                continue
                            st.caption(f"{icon} {type_name} ({len(sources_list)} 筆)")
                            for source in sources_list:
                                with st.expander(f"{icon} {source['filename']}"):
                                    st.markdown(f"> {source['snippet'][:300]}...")
                                    if source.get('original_url'):
                                        st.markdown(f"[🔗 查看原始網頁]({source['original_url']})")
                    else:
                        st.info("你查詢的問題在目前的文件庫中沒有合適的結果，請嘗試換個方式描述您的問題。")

    # 範例問題
    if not question:
        st.markdown("---")
        st.subheader("💡 範例問題")

        cols = st.columns(2)
        for idx, eq in enumerate(EXAMPLE_QUESTIONS):
            col = cols[idx % 2]
            with col:
                if st.button(f"📌 {eq}", key=f"example_{idx}", use_container_width=True):
                    st.session_state.current_question = eq
                    st.rerun()


if __name__ == "__main__":
    main()
