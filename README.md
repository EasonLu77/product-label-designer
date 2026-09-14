# Product Label Designer v0.9

## 網頁版部署

程式入口為儲存庫根目錄的 `app.py`。Streamlit Community Cloud 設定與本機啟動方式見 [DEPLOYMENT.md](DEPLOYMENT.md)。
App: https://easonlu77-label-designer.streamlit.app/
## 本版版面

左欄各區塊同寬，依序為：專案存檔／讀取、① 產品資訊、② 功能規格、③ 目標市場、排版／配色與大小、marking 來源。
目標市場預設收合，展開後可勾選多個市場並管理 marking。
右欄保留 Label 即時預覽與 PNG 下載。既有 v0.8 專案檔可直接讀取。

## RFID 與 ID

- 純被動標籤：一般不需要標籤自己的 FCC ID。加拿大 RSS-310 Issue 6 §2.2／§3.2 免認證，並豁免被動 RFID 標籤的測試報告、標示與手冊要求。被動標籤定義重點在於不使用自有電源進行 RF 發射；有電池但僅用於感測等用途，不一定屬於主動發射標籤。
- 讀寫器／主動發射標籤：通常需要依相應發射器規定認證及標示，但部分低頻／低功率設備有例外。FCC §15.201(a) 允許符合指定條件的低於 490 kHz 設備走 SDoC；加拿大 RSS-310 的 Category II 設備免認證。因此不能僅依 RFID 名稱斷言一定要有 FCC／IC ID。
- 主機中的被動標籤豁免不代表主機其他電路或發射器豁免。
- 本版 RFID 連動維持：Passive tag only 不開啟 ID；Reader/writer 或 Active tag 開啟共用 ID 輸入。開啟欄位只提供填寫功能，不表示已判定認證強制性。

來源：[FCC RFID 培訓資料，第 26 頁](https://www.fcc.gov/oet/ea/presentations/files/oct07/Oct_07-Basics_of_Unlicensed_Trans-JD.pdf)、[47 CFR §15.201](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-C/section-15.201)、[RSS-310](https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-310-licence-exempt-radio-apparatus-category-ii-equipment)。FCC 培訓資料為歷史解釋，特定產品仍應核對適用的現行規定。

## 既有功能

- Class I 不再自動把「Class I」文字印在 Label；Class II／III 保留符號連動。
- 「② 功能規格」預設收合，點標題展開。內建及自訂功能都用兩欄排列。
- Wi-Fi、Bluetooth、Cellular、主動 RFID／NFC、自訂 RF 功能共用一組 FCC ID／IC ID。
- 加入完整專案存檔與讀取，保留原有 PNG 下載。

## 存檔與讀取

左欄上方展開「專案存檔／讀取」：

1. 按「儲存專案」，瀏覽器下載 product_label_project.json。
2. 下次使用或換電腦時，選擇先前的 JSON 專案檔，再按「讀取專案」。
3. 讀取會取代目前內容，恢復產品資訊、功能規格、自訂功能、共用 RF ID、目標市場、手動 marking、圖檔、來源、勾選結果與排版設定。

圖檔內嵌在專案檔中，不需要另外保存 PNG 素材。檔案上限 150 MB。
格式或版本錯誤的檔案會被拒絕，目前內容不會被取代。
存檔是手動下載至電腦，不是自動存檔或雲端帳號同步，關閉／重新整理前請先存檔。
「儲存 marking」只更新目前工作階段；要保留到下次，仍需按「儲存專案」。

## 共用 RF ID

至少一個 RF 功能啟用時，顯示一組共用欄位：

- 整機 ID：FCC ID:／IC:。
- 內含認證模組：Contains FCC ID:／Contains IC:。
- 選美國才加入 FCC ID，選加拿大才加入 IC ID，留白不輸出。
- 全部 RF 功能取消時 ID 不印到 Label，但編號仍保留，重新勾選可恢復。
- 新增或刪除自訂功能不清除共用 ID。
- 共用欄位適用於同一組認證編號；多個不同認證模組可使用手動文字 marking 加入其他編號。
- Passive tag only 不觸發本版 ID 連動。自訂功能需指定為 RF 發射功能才觸發。

## Class I 與其他連動

Class I 不是本工具應自動加上的通用必要文字。保護接地符號 IEC 60417-5019 是接地端子識別，應依適用產品標準處理，未用它替代 Class I 整機標示。
Class II／III 使用 IEC 60417-5172／5180 的圖示草稿，正式使用仍需核對產品標準及圖形要求。

選加拿大且 EMC Class 為 A／B，會加入對應 CAN ICES-003(A) / NMB-003(A) 或 CAN ICES-003(B) / NMB-003(B)。取消加拿大或選「尚未確認」即移除。以使用者已確認 ICES-003 適用為前提。
其他 marking 維持手動勾選，新增市場是空的手動清單。產品類別為自由文字備註，不參與連動。

## 來源

- IEC 符號：[5019](https://www.iso.org/obp/ui/#iec:grs:60417:5019)、[5172](https://www.iso.org/obp/ui/#iec:grs:60417:5172)、[5180](https://www.iso.org/obp/ui/#iec:grs:60417:5180)。
- [ICES-003 §4.2](https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/interference-causing-equipment-standards-ices/ices-003-information-technology-equipment-including-digital-apparatus)。
- [RSS-Gen §9.4.4](https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-gen-general-requirements-compliance-radio-apparatus)。
- [47 CFR §15.212](https://www.ecfr.gov/current/title-47/section-15.212)。

## 更新啟動

停止舊版（命令視窗 Ctrl+C），把新版 compliance_checker 內容覆蓋到原本同名資料夾。
保留 .venv，雙擊 start_label_designer.bat；頂部應顯示 v0.9。
無新增套件需求。本次在 Linux 驗證，未執行 Windows batch。

## 程式結構

- data/manual_markings.json：手動 marking 範例與來源。
- data/linked_markings.json：保護類別、加拿大 EMC 與 RF ID 連動資料。
- compliance/manual_catalog.py：市場、marking、自訂功能與資料驗證。
- compliance/linked_markings.py：指定連動。
- compliance/project_io.py：版本化 JSON 專案存檔及讀取。
- compliance/label_designer.py：產品資料驗證及 PNG 繪圖。
- app.py：介面與互動。

測試：python -m pytest tests/test_manual_catalog.py tests/test_linked_markings.py tests/test_project_io.py -q
