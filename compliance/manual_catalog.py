"""Manual catalog with a small, explicit set of linked markings."""
import base64
import copy
import hashlib
from uuid import uuid4
from .label_designer import DEFAULT, validate_project as validate_base_project, validate_png, validate_rule, delete_market
from .engine import ROOT, read_json

DOMAINS=['EMC','Safety','RF','Energy','Environmental','Other']

def make_project():
    p=copy.deepcopy(DEFAULT)
    p.update(custom_features=[],radio_ids={'shared':{'mode':'device','fcc_id':'','ic_id':''}})
    for market in p['market_catalog']:
        for item in read_json(ROOT/'data/manual_markings.json')['items']:
            if market in item['markets']:
                row=copy.deepcopy(item)
                row.update(id=market+'_'+item['id'],markets=[market],when=None,selected=False)
                p['market_rules'].append(row)
    return p

def add_market(p,name):
    name=name.strip()
    if not name or len(name)>40:raise ValueError('市場名稱需為 1–40 字元')
    if name.casefold() in {v.casefold() for v in p['market_catalog'].values()}:raise ValueError('此市場名稱已存在')
    if len(p['market_catalog'])>=30:raise ValueError('最多可設定 30 個市場')
    key='CUSTOM_'+uuid4().hex[:10]
    p['market_catalog'][key]=name;p['markets'].append(key)
    return key

def save_marking(p,market,*,title,domains,kind,content='',png=None,key=None,official_artwork_url='',regulation='',reference='',note=''):
    if market not in p['market_catalog']:raise ValueError('市場不存在')
    existing=next((r for r in p['market_rules'] if r['id']==key and r['markets']==[market]),None)
    if key and existing is None:raise ValueError('Marking 不存在')
    if not domains or not set(domains)<=set(DOMAINS):raise ValueError('請選擇至少一個 requirement 分類')
    if kind not in ['symbol','text']:raise ValueError('請選擇 PNG 圖檔或文字')
    if not existing and len(p['market_rules'])>=240:raise ValueError('Marking 最多 240 個')
    artwork_key=None
    if kind=='symbol':
        if png:
            validate_png(png)
            artwork_key='img_'+hashlib.sha256(png).hexdigest()[:32]
            content=artwork_key
        elif existing and existing['kind']=='symbol':content=existing['content']
        else:raise ValueError('請上傳 PNG 圖檔')
    row=dict(id=key or 'M_'+uuid4().hex[:12],title=title.strip(),domains=list(dict.fromkeys(domains)),markets=[market],when=None,kind=kind,content=content.strip(),reference=reference.strip(),note=note,official_artwork_url=official_artwork_url.strip(),regulation=regulation,selected=existing.get('selected',False) if existing else False)
    validate_rule(row,p['market_catalog'],custom=True)
    if row['official_artwork_url'] and not row['official_artwork_url'].startswith(('https://','http://')):raise ValueError('來源網址須以 https:// 或 http:// 開頭')
    if artwork_key and artwork_key not in p['artwork'] and len(p['artwork'])>=50:raise ValueError('最多可上傳 50 張 PNG')
    if artwork_key:p['artwork'][artwork_key]=base64.b64encode(png).decode()
    if existing is not None:existing.clear();existing.update(row)
    else:p['market_rules'].append(row)
    return row['id']

def delete_marking(p,key):
    p['market_rules']=[r for r in p['market_rules'] if r['id']!=key]
    used={r['content'] for r in p['market_rules'] if r['kind']=='symbol'}
    p['artwork']={k:v for k,v in p['artwork'].items() if k in used}

def select_items(p):
    validate_project(p)
    from .linked_markings import linked_items
    seen=set();rows=[]
    for row in linked_items(p):
        identity=(row["kind"],row["content"])
        if identity not in seen:
            rows.append({**row,"included":True,"render_text":row["content"],"automatic":True});seen.add(identity)
    for row in p['market_rules']:
        if not set(row['markets']) & set(p['markets']):continue
        identity=(row['kind'],row['content'])
        selected=bool(row.get('selected',False))
        included=selected and identity not in seen
        if included:seen.add(identity)
        rows.append({**row,'included':included,'render_text':row['content'],'duplicate_on_label':selected and not included})
    return rows


def validate_project(p):
    import re
    if not isinstance(p,dict):raise ValueError('專案格式錯誤')
    validate_base_project({k:v for k,v in p.items() if k not in ['custom_features','radio_ids']})
    if len(p['market_catalog'])>30:raise ValueError('最多可設定 30 個市場')
    for key,name in p['market_catalog'].items():
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key) or len(name)>40:raise ValueError('市場格式錯誤')
    if not isinstance(p.get('custom_features'),list) or len(p['custom_features'])>40:raise ValueError('自訂功能最多 40 個')
    seen=set()
    for row in p['custom_features']:
        if not isinstance(row,dict) or set(row)!={'id','name','selected','is_rf'}:raise ValueError('自訂功能格式錯誤')
        if not isinstance(row['id'],str) or not re.fullmatch(r'F_[A-Za-z0-9_-]{1,60}',row['id']) or row['id'] in seen:raise ValueError('自訂功能 ID 格式錯誤或重複')
        seen.add(row['id'])
        if not isinstance(row['name'],str) or not row['name'].strip() or len(row['name'])>40 or type(row['selected']) is not bool or type(row['is_rf']) is not bool:raise ValueError('自訂功能格式錯誤')
    if not isinstance(p.get('radio_ids'),dict) or set(p['radio_ids'])!={'shared'}:raise ValueError('共用 RF ID 格式錯誤')
    entry=p['radio_ids']['shared']
    if not isinstance(entry,dict) or set(entry)!={'mode','fcc_id','ic_id'} or entry['mode'] not in ['device','module']:raise ValueError('RF ID 類型錯誤')
    for field in ['fcc_id','ic_id']:
        if not isinstance(entry[field],str) or len(entry[field])>80 or any(ord(c)<32 for c in entry[field]):raise ValueError('RF ID 須為 80 字元內的單行文字')
    for row in p['market_rules']:
        if row.get('when') is not None or row['kind'] not in ['symbol','text'] or type(row.get('selected')) is not bool:raise ValueError('手動 marking 格式錯誤')
        if len(row['markets'])!=1:raise ValueError('每個手動 marking 須屬於一個市場')
        domains=row.get('domains')
        if not isinstance(domains,list) or not domains or not all(isinstance(d,str) and d in DOMAINS for d in domains):raise ValueError('Marking 分類錯誤')
        for field in ['reference','official_artwork_url','note','regulation']:
            value=row.get(field,'')
            if not isinstance(value,str) or len(value)>10000:raise ValueError('Marking 來源格式錯誤')
            if field in ['reference','official_artwork_url'] and value and not value.startswith(('https://','http://')):raise ValueError('來源網址格式錯誤')
    for key in p['artwork']:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key):raise ValueError('圖檔識別碼錯誤')


def add_feature(p,name,is_rf=False):
    name=name.strip()
    if not name or len(name)>40:raise ValueError('功能名稱需為 1–40 字元')
    existing={'wi-fi','bluetooth','cellular','rfid / nfc','rfid','nfc','數位電路'}|{r['name'].casefold() for r in p['custom_features']}
    if name.casefold() in existing:raise ValueError('此功能名稱已存在')
    if len(p['custom_features'])>=40:raise ValueError('自訂功能最多 40 個')
    key='F_'+uuid4().hex[:12]
    p['custom_features'].append({'id':key,'name':name,'is_rf':bool(is_rf),'selected':False})
    return key

def delete_feature(p,key):
    p['custom_features']=[r for r in p['custom_features'] if r['id']!=key]
    # Shared RF IDs belong to the project and survive feature deletion.
