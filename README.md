# 金管會智能問答系統

AI 驅動的金融監督管理委員會資料查詢系統，支援裁罰案件、法令函釋、重要公告的智能問答。

## 功能特色

- 🔍 **多資料來源查詢**：可同時查詢裁罰案件、法令函釋、重要公告
- 🤖 **AI 智能問答**：使用 Gemini File Search 進行語意搜尋
- 📚 **來源追蹤**：顯示答案的參考來源文件
- 💡 **範例問題**：提供常見查詢範例

## 資料來源

| 類型 | 筆數 | 說明 |
|-----|-----|------|
| 裁罰案件 | 490 | 金融機構違規裁罰記錄 (2012-2025) |
| 法令函釋 | 2,872 | 法規解釋、修正說明、條文對照 |
| 重要公告 | 1,642 | 金管會政策公告、法規修正公告 |

## 本地開發

```bash
# 安裝依賴
pip install -r requirements.txt

# 設定環境變數
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# 編輯 secrets.toml 填入 GEMINI_API_KEY

# 啟動應用
streamlit run app/main.py
```

## 部署到 Streamlit Cloud

1. Fork 此專案到你的 GitHub
2. 前往 [Streamlit Cloud](https://share.streamlit.io/)
3. 連接你的 GitHub 帳號
4. 選擇此專案
5. 在 Secrets 設定中加入 `GEMINI_API_KEY`

## 技術架構

- **前端**：Streamlit
- **AI 引擎**：Google Gemini 2.5 Flash + File Search
- **資料格式**：Plain Text (優化後的 RAG 格式)

## 注意事項

- 本系統僅供參考，不構成法律建議
- 查詢結果基於已收錄的文件，可能不包含最新資料
