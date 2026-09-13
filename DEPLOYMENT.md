# Streamlit Community Cloud 部署

1. 登入 https://share.streamlit.io/，選擇 Create app，從 GitHub 部署。
2. Repository：`EasonLu77/product-label-designer`
3. Branch：`main`
4. Main file path：`app.py`
5. Advanced settings：Python 選擇 `3.12`。本程式不需要 secrets 或 API key。
6. 點擊 Deploy，等待依賴安裝及啟動完成。
7. 確認應用程式分享設定允許任何人查看，再分享實際產生的 `https://…streamlit.app/` 網址。

`requirements.txt` 安裝 Python 套件，`packages.txt` 安裝 Linux 中文字型，確保中文 PNG 輸出。
程式入口、資料、素材及 `.streamlit/config.toml` 均置於儲存庫根目錄下。

## 本機執行

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

## 驗證

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

各瀏覽器工作階段獨立。請使用「儲存專案」下載 JSON 備份；重新整理、關閉分頁或雲端重啟後，不保證保留未下載的工作內容。

官方說明：https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
