from __future__ import annotations
import copy
import streamlit as st
from compliance.label_designer import FIELDS,TEXT_FIELDS,make_layout,render_png
from compliance.engine import ROOT,read_json
from compliance.manual_catalog import make_project,add_market,delete_market,save_marking,delete_marking,select_items,DOMAINS,validate_project,add_feature,delete_feature
from compliance.linked_markings import active_radios,linked_items
from compliance.project_io import dump_project,load_project

st.set_page_config(page_title='Product Label Designer',page_icon='🏷️',layout='wide')
st.title('Product Label Designer')
st.caption('手動 marking ＋ 保護類別、加拿大 EMC、RF ID 連動 · v0.9')

def install(p):
    validate_project(p)
    st.session_state.label_project=copy.deepcopy(p)
    for k in TEXT_FIELDS+['width_mm','height_mm','template','theme']:st.session_state['label_'+k]=p[k]
    for k in FIELDS:st.session_state['label_'+k]=p['facts'][k]
    for m in p['market_catalog']:st.session_state['market_'+m]=m in p['markets']
    for k in list(st.session_state):
        if k.startswith('include_'):del st.session_state[k]

if '_loaded_project' in st.session_state:
    loaded=st.session_state.pop('_loaded_project')
    validate_project(loaded)
    for key in list(st.session_state):del st.session_state[key]
    install(loaded)
    st.session_state.label_ui_version='0.9.0'
    st.session_state._loaded_notice=True

if st.session_state.get('label_ui_version')!='0.9.0':
    for k in list(st.session_state):
        if k.startswith(('label_','market_','include_')):del st.session_state[k]
    install(make_project());st.session_state.label_ui_version='0.9.0'
p=copy.deepcopy(st.session_state.label_project)
if st.session_state.pop('_loaded_notice',False):st.success('專案已讀取，可繼續編輯。')

def marking_form(market,row=None):
    row=row or {}
    key=row.get('id')
    with st.form('marking_'+(key or market),clear_on_submit=not bool(key)):
        title=st.text_input('Marking 名稱',value=row.get('title',''),max_chars=60)
        domains=st.multiselect('Requirement 分類',DOMAINS,default=row.get('domains',[]))
        kind=st.selectbox('標示類型',['symbol','text'],index=1 if row.get('kind')=='text' else 0,format_func=lambda k:'PNG 圖檔' if k=='symbol' else '文字')
        content=st.text_area('Label 文字（文字類型使用）',value=row.get('content','') if row.get('kind')=='text' else '',max_chars=250)
        png=st.file_uploader('Marking PNG（圖檔類型使用）',type=['png'])
        st.caption('PNG 請使用黑色圖案，白色或透明背景，最大 2 MB；編輯時留空可保留原圖。')
        official=st.text_input('圖檔官方來源網址',value=row.get('official_artwork_url',''))
        regulation=st.text_input('相關規範',value=row.get('regulation',''))
        reference=st.text_input('規範來源網址',value=row.get('reference',''))
        note=st.text_area('備註（不印到 Label）',value=row.get('note',''))
        if st.form_submit_button('儲存 marking' if key else '新增 marking'):
            try:
                save_marking(p,market,title=title,domains=domains,kind=kind,content=content,png=png.getvalue() if png else None,key=key,official_artwork_url=official,regulation=regulation,reference=reference,note=note)
                st.success('已儲存。請勾選要加入 Label 的 marking。')
            except ValueError as exc:st.error(str(exc))

left,right=st.columns([1,1.65],gap='large')
with left:
    with st.expander('專案存檔／讀取',expanded=False):
        save_slot=st.container()
        st.caption('保存產品資料、市場、marking 圖檔、ID 與勾選結果。')
        uploaded=st.file_uploader('選擇專案檔（JSON）',type=['json'],key='project_upload')
        if st.button('讀取專案',disabled=uploaded is None):
            try:
                st.session_state._loaded_project=load_project(uploaded.getvalue())
                st.rerun()
            except ValueError as exc:st.error('未讀取，現有內容保持不變：'+str(exc))
        st.caption('讀取會取代目前內容，請先存檔保留修改。')
    with st.expander('① 產品資訊',expanded=False):
        for k,label in [('brand','公司／品牌'),('model','Model／型號'),('description','產品名稱')]:p[k]=st.text_input(label,key='label_'+k,max_chars=250)
        p['facts']['category']=st.text_input('產品類別（自訂，不影響 Label）',key='label_category',max_chars=100)
        defs=read_json(ROOT/'data/fields.json')
        cols=st.columns(2)
        p['facts']['power']=cols[0].selectbox('供電方式',['AC','DC','AC/DC','Battery only'],key='label_power')
        p['facts']['safety_class']=cols[1].selectbox('整機保護類別',[None,'I','II','III'],format_func=lambda x:'尚未確認' if x is None else 'Class '+x,key='label_safety_class')
        cols=st.columns(3)
        for col,k,label in zip(cols,['voltage','current','frequency'],['電壓 V','電流 A','頻率 Hz']):p[k]=col.text_input(label,key='label_'+k,max_chars=60)
        cols=st.columns(2)
        p['facts']['psu']=cols[0].selectbox('電源供應器',defs['psu']['options'],key='label_psu')
        p['facts']['environment']=cols[1].selectbox('使用環境',defs['environment']['options'],key='label_environment')
        st.caption('Class I 不自動印出類別文字；Class II／III 顯示符號草稿。接地端子標示依產品標準另行確認。')
        p['facts']['emc_class']=st.selectbox('EMC Class',[None,'A','B'],format_func=lambda x:'尚未確認' if x is None else x,key='label_emc_class')
        st.caption('選取加拿大時，依 EMC Class 自動加入 ICES-003 文字；前提是已確認產品適用 ICES-003。')
        p['origin']=st.text_input('原產地（Made in）',key='label_origin',max_chars=100)
        p['address']=st.text_input('製造商／責任業者地址（選填）',key='label_address',max_chars=250)
    with st.expander('② 功能規格',expanded=False):
        st.caption('RF 功能可連動 FCC ID／IC ID；其他自訂功能供自行判斷。')
        cols=st.columns(2)
        for i,(k,label) in enumerate([('digital','數位電路'),('wifi','Wi-Fi'),('bluetooth','Bluetooth'),('cellular','Cellular')]):p['facts'][k]=cols[i%2].checkbox(label,key='label_'+k)
        p['facts']['rfid']=st.selectbox('RFID / NFC',['None','Passive tag only','Reader/writer','Active tag'],key='label_rfid',help='Passive tag only 是僅含被動標籤；Reader/writer 或 Active tag 會開啟共用 ID 欄位，但是否需認證及標示，仍依頻率、功率與適用規定確認。')

        with st.popover('新增／刪除功能',width='stretch'):
            with st.form('add_feature',clear_on_submit=True):
                feature_name=st.text_input('功能名稱',max_chars=40,placeholder='例如：Zigbee、Ethernet')
                is_rf=st.checkbox('此功能具有 RF 發射功能（連動 FCC ID／IC ID）')
                if st.form_submit_button('新增功能'):
                    try:add_feature(p,feature_name,is_rf);st.success('已新增，請勾選產品具備的功能。')
                    except ValueError as exc:st.error(str(exc))
            if p['custom_features']:
                remove_features=st.multiselect('刪除自訂功能',[r['id'] for r in p['custom_features']],format_func={r['id']:r['name'] for r in p['custom_features']}.get)
                if st.button('刪除所選功能',disabled=not remove_features):
                    for key in remove_features:
                        delete_feature(p,key);st.session_state.pop('feature_'+key,None)
                    st.success('已刪除功能，共用 ID 保留。')
        custom_cols=st.columns(2)
        for i,feature in enumerate(p['custom_features']):
            feature['selected']=custom_cols[i%2].checkbox(feature['name']+('（RF）' if feature['is_rf'] else ''),value=feature['selected'],key='feature_'+feature['id'])
        radios=active_radios(p)
        if radios:
            ids=p['radio_ids']['shared']
            st.markdown('**共用 FCC ID / IC ID**')
            st.caption('啟用的 RF 功能：'+', '.join(name for _,name in radios))
            ids['mode']=st.selectbox('ID 標示方式',['device','module'],index=0 if ids['mode']=='device' else 1,format_func=lambda value:'整機 ID' if value=='device' else '內含認證模組（Contains）',key='radio_mode_shared')
            id_cols=st.columns(2)
            ids['fcc_id']=id_cols[0].text_input('FCC ID',value=ids['fcc_id'],key='fcc_shared',max_chars=80,placeholder='僅輸入編號')
            ids['ic_id']=id_cols[1].text_input('IC ID',value=ids['ic_id'],key='ic_shared',max_chars=80,placeholder='僅輸入編號')
            st.caption('共用一組編號，只需填一次。選美國才印 FCC ID，選加拿大才印 IC ID；全部 RF 功能取消時隱藏，編號仍保留。')
        else:st.caption('勾選 RF 功能後可填共用 FCC ID／IC ID。')

    with st.expander('③ 目標市場',expanded=False):
        with st.popover('新增／刪除市場',width='stretch'):
            with st.form('add_market',clear_on_submit=True):
                name=st.text_input('市場名稱',placeholder='例如：日本 JP',max_chars=40)
                if st.form_submit_button('新增市場'):
                    try:
                        key=add_market(p,name)
                        st.session_state['market_'+key]=True
                        st.success('已新增並選取市場。')
                    except ValueError as exc:st.error(str(exc))
            st.caption('新增市場後，請在該市場下建立自己的 marking。')
            if p['market_catalog']:
                remove=st.multiselect('選擇要刪除的市場',list(p['market_catalog']),format_func=p['market_catalog'].get)
                if st.button('刪除所選市場',disabled=not remove):
                    for market in remove:
                        delete_market(p,market)
                        st.session_state.pop('market_'+market,None)
                    st.success('已刪除所選市場。')
        cols=st.columns(2);p['markets']=[]
        for i,(m,label) in enumerate(p['market_catalog'].items()):
            if cols[i%2].checkbox(label,key='market_'+m):p['markets'].append(m)

        for market in p['markets']:
            with st.expander(p['market_catalog'][market]+' · marking',expanded=True):
                with st.popover('新增 marking',key='add_mark_'+market):
                    marking_form(market)
                market_rows=[r for r in p['market_rules'] if r['markets']==[market]]
                if market_rows:
                    with st.expander('編輯／刪除 marking'):
                        chosen=st.selectbox('選擇 marking',[r['id'] for r in market_rows],format_func={r['id']:r['title'] for r in market_rows}.get,key='edit_'+market)
                        row=next(r for r in market_rows if r['id']==chosen)
                        marking_form(market,row)
                        if st.button('刪除此 marking',key='delete_'+chosen):
                            delete_marking(p,chosen)
                            st.session_state.pop('pick_'+chosen,None)
                            st.success('已刪除。')
                    for row in [r for r in p['market_rules'] if r['markets']==[market]]:
                        row['selected']=st.checkbox(row['title']+' · '+', '.join(row['domains']),value=row.get('selected',False),key='pick_'+row['id'])
                else:st.caption('尚未建立手動 marking。請點「新增 marking」。')

    with st.expander('排版、配色與大小',expanded=True):
        cols=st.columns(2)
        p['template']=cols[0].selectbox('排版',['split','bottom'],format_func=lambda x:'左文右圖' if x=='split' else '圖示置底',key='label_template')
        p['theme']=cols[1].selectbox('標籤配色',['dark','light'],format_func=lambda x:'黑底白字' if x=='dark' else '白底黑字',key='label_theme')
        cols=st.columns(2)
        p['width_mm']=cols[0].number_input('寬度 mm',min_value=35,max_value=200,key='label_width_mm')
        p['height_mm']=cols[1].number_input('高度 mm',min_value=35,max_value=200,key='label_height_mm')
    with st.expander('marking 來源',expanded=False):
        for item in linked_items(p):
            st.write(item['title']+'（自動連動）')
            st.markdown('[規範／符號來源]('+item['reference']+')')
            if item.get('note'):st.caption(item['note'])
        source_markets=[m for m in p['market_catalog'] if any(r['markets']==[m] for r in p['market_rules'])]
        if source_markets:
            source_market=st.selectbox('來源所屬市場',source_markets,format_func=p['market_catalog'].get)
            source_rows=[r for r in p['market_rules'] if r['markets']==[source_market]]
            source_key=st.selectbox('標註哪個 marking',[r['id'] for r in source_rows],format_func=lambda k:next(r['title'] for r in source_rows if r['id']==k))
            source_row=next(r for r in source_rows if r['id']==source_key)
            with st.form('source_'+source_key):
                official=st.text_input('圖檔官方來源網址',value=source_row.get('official_artwork_url',''))
                regulation=st.text_input('相關規範／標準／條文',value=source_row.get('regulation',''))
                ref=st.text_input('規範來源網址（選填）',value=source_row.get('reference',''))
                note=st.text_area('來源備註',value=source_row.get('note',''))
                if st.form_submit_button('更新 marking 來源'):
                    try:
                        save_marking(p,source_market,key=source_key,title=source_row['title'],domains=source_row['domains'],kind=source_row['kind'],content=source_row['content'],official_artwork_url=official,regulation=regulation,reference=ref,note=note)
                        st.success('已標註來源與相關規範。')
                    except ValueError as exc:st.error(str(exc))
            st.caption('可為內建與新增 marking 分別標註；填入網址不會自動下載圖檔或驗證規範。')
        else:st.caption('請先在市場下新增 marking。')

with right:
    st.subheader('Label 即時預覽')
    preview=st.container()
    with preview:
        if not p['markets']:st.info('尚未選擇市場：目前顯示產品資料與整機保護類別。')
        try:
            rows=select_items(p)
            layout=make_layout(p,rows);png=render_png(layout)
            st.image(png,width='stretch')
            st.caption(f"{p['width_mm']} × {p['height_mm']} mm · PNG 300 dpi · Label 草稿")
            st.download_button('下載 Label PNG',png,'product_label_draft.png','image/png',width='stretch')
            st.caption('包含手動勾選的 marking 及指定連動項目。新增手動 marking 預設不勾選。')
        except ValueError as exc:st.error(str(exc))
st.session_state.label_project=copy.deepcopy(p)

with save_slot:
    try:
        saved=dump_project(p)
        st.download_button('儲存專案',saved,'product_label_project.json','application/json',width='stretch')
    except ValueError as exc:st.error('暫時無法存檔：'+str(exc))
