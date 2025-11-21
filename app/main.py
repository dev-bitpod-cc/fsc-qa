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
from typing import List, Dict, Any

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

                            # 提取資訊
                            filename = "未知文件"
                            if hasattr(context, 'title') and context.title:
                                filename = context.title
                            elif hasattr(context, 'uri') and context.uri:
                                filename = context.uri.split('/')[-1]

                            snippet = ""
                            if hasattr(context, 'text') and context.text:
                                snippet = context.text[:500]

                            score = 1.0
                            if hasattr(chunk, 'score'):
                                score = float(chunk.score)

                            sources.append({
                                'filename': filename,
                                'snippet': snippet,
                                'score': score,
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

                # 指標欄
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ 回應時間", f"{result['latency']:.2f} 秒")
                with col2:
                    st.metric("📚 來源數量", len(result['sources']))
                with col3:
                    stores_text = ", ".join([STORES[s]['display_name'] for s in selected_stores])
                    st.metric("📂 查詢範圍", stores_text[:20])

                st.markdown("---")

                # 答案
                st.subheader("📝 答案")
                st.markdown(result['answer'])

                st.markdown("---")

                # 來源
                if result['sources']:
                    st.subheader(f"📚 參考來源 ({len(result['sources'])} 筆)")

                    for i, source in enumerate(result['sources'], 1):
                        with st.expander(
                            f"來源 {i}: {source['filename'][:60]}...",
                            expanded=False
                        ):
                            st.markdown(f"**相關內容：**")
                            st.markdown(f"> {source['snippet'][:300]}...")

                            if source['score'] < 1.0:
                                st.caption(f"相似度: {source['score']:.2%}")
                else:
                    # sources=0 自動重試
                    st.warning("⚠️ 未找到參考來源，正在重試...")
                    with st.spinner("重新查詢中..."):
                        result2 = query_gemini(question, selected_stores, api_key)

                    if result2['sources']:
                        st.success("✅ 重試成功")
                        st.markdown(result2['answer'])

                        for i, source in enumerate(result2['sources'], 1):
                            with st.expander(f"來源 {i}: {source['filename'][:60]}..."):
                                st.markdown(f"> {source['snippet'][:300]}...")
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
