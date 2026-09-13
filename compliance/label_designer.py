"""Label composition is separate from legal assessment. Outputs are always drafts."""
from __future__ import annotations
import base64
import io
import json
import math
from html import escape
from pathlib import Path
from string import Formatter
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops
from .engine import ROOT, evaluate, validate_expression, validate_fact, read_json

VERSION='0.4.0'
BASE_MARKETS={'US':'美國 US','CA':'加拿大 CA','EU':'歐盟 EU','AU':'澳洲 AU'}
DEFAULT={'schema_version':'label-3','brand':'YOUR COMPANY','model':'PRINTER-100','description':'Digital Photo Printer','origin':'Taiwan','address':'','voltage':'100–240','current':'5.0','frequency':'50/60','markets':['US','CA','EU','AU'],'market_catalog':BASE_MARKETS.copy(),'market_rules':[],'facts':{'category':'Printer','power':'AC','safety_class':'I','psu':'Internal','environment':'Indoor','digital':True,'wifi':False,'bluetooth':False,'cellular':False,'rfid':'None','battery':False,'laser':False,'emc_class':'A'},'width_mm':110,'height_mm':55,'template':'split','theme':'dark','artwork':{}}
TEXT_FIELDS=['brand','model','description','origin','address','voltage','current','frequency']
FIELDS=['category','power','safety_class','psu','environment','digital','wifi','bluetooth','cellular','rfid','battery','laser','emc_class']

def rule_fields():
    # Category is metadata only: it is intentionally unavailable to rules.
    return {k:v for k,v in read_json(ROOT/'data/fields.json').items() if k in FIELDS and k!='category'}

def validate_rule(row,catalog,custom=False):
    import re
    if not isinstance(row,dict):raise ValueError('Invalid marking')
    for k in ['id','title','markets','when','kind','content','reference','note']:
        if k not in row:raise ValueError('Missing marking field: '+k)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',row['id']):raise ValueError('Invalid marking ID')
    if not isinstance(row['title'],str) or not row['title'].strip() or len(row['title'])>60:raise ValueError('Marking 名稱需為 1–60 字元')
    if not isinstance(row['markets'],list) or not row['markets'] or not set(row['markets'])<=set(catalog):raise ValueError('請選擇有效的適用市場')
    if row['kind'] not in ['symbol','text','placeholder','task']:raise ValueError('Invalid marking type')
    if not isinstance(row['content'],str) or len(row['content'])>250:raise ValueError('標示文字最多 250 字元')
    if row['kind']=='symbol' and not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',row['content']):raise ValueError('Invalid artwork key')
    if row['kind']=='text' and not row['content'].strip():raise ValueError('請輸入 Label 上的文字')
    if row['reference'] and not row['reference'].startswith(('https://','http://')):raise ValueError('來源網址須以 https:// 或 http:// 開頭')
    if row['when'] is not None:validate_expression(row['when'],rule_fields())
    elif not custom:raise ValueError('Built-in rules require a condition')
    if not custom:
        if any(k!='emc_class' for _,k,_,_ in Formatter().parse(row['content']) if k):raise ValueError('Unknown text substitution')

def load_label_rules():
    pack=read_json(ROOT/'data/label_rules.json')
    ids=set()
    for row in pack['items']:
        if row['id'] in ids:raise ValueError('Duplicate label rule ID')
        ids.add(row['id']);validate_rule(row,BASE_MARKETS)
    return pack

def validate_png(raw):
    if len(raw)>2_000_000:raise ValueError('請使用 2 MB 以內的 PNG')
    try:
        im=Image.open(io.BytesIO(raw))
        if im.format!='PNG' or im.width*im.height>4_000_000:raise ValueError('圖檔須為 4 百萬像素內 PNG')
        im.verify()
        check=Image.open(io.BytesIO(raw)).convert('RGBA')
    except (OSError,SyntaxError) as exc:
        raise ValueError('無法讀取 PNG，請使用有效的 PNG 圖檔') from exc
    alpha=ImageChops.multiply(ImageOps.invert(check.convert('L')),check.getchannel('A'))
    if not alpha.getbbox():raise ValueError('圖檔沒有可顯示的黑色圖案；請使用黑色 PNG，可含透明背景')

def validate_project(p):
    if not isinstance(p,dict) or set(p)!=set(DEFAULT):raise ValueError('Label 設定格式不符')
    if p['schema_version']!='label-3':raise ValueError('不支援的設定版本')
    for k in TEXT_FIELDS:
        if not isinstance(p[k],str) or len(p[k])>250:raise ValueError(k+' 必須是 250 字元內的文字')
    for k in ['brand','model','description','origin','voltage','current']:
        if not p[k].strip():raise ValueError('請填寫 '+k)
    for k in ['width_mm','height_mm']:
        if type(p[k]) not in [int,float] or not math.isfinite(p[k]) or not 35<=p[k]<=200:raise ValueError('標籤尺寸須在 35–200 mm')
    for k in ['markets']:
        if not isinstance(p[k],list) or any(not isinstance(x,str) for x in p[k]) or len(set(p[k]))!=len(p[k]):raise ValueError('Invalid '+k)
    if not isinstance(p['market_catalog'],dict) or any(not isinstance(k,str) or not isinstance(v,str) or not v.strip() for k,v in p['market_catalog'].items()):raise ValueError('Invalid market catalog')
    if not set(p['markets'])<=set(p['market_catalog']):raise ValueError('Unknown market')
    if p['template'] not in ['split','bottom'] or p['theme'] not in ['dark','light']:raise ValueError('Unknown template/theme')
    if set(p['facts'])!=set(FIELDS):raise ValueError('產品規格欄位不符')
    if not isinstance(p['facts']['category'],str) or len(p['facts']['category'])>100:raise ValueError('產品類別最多 100 字元')
    definitions=rule_fields()
    for k,v in p['facts'].items():
        if k!='category':validate_fact(v,definitions[k])
    for key in ['digital','wifi','bluetooth','cellular','battery','laser']:
        if type(p['facts'][key]) is not bool:raise ValueError('Feature checkbox requires true/false')
    if not isinstance(p['market_rules'],list) or len(p['market_rules'])>240:raise ValueError('Marking 最多 240 個')
    ids=set()
    for row in p['market_rules']:
        validate_rule(row,p['market_catalog'],custom=True)
        if row['id'] in ids:raise ValueError('Duplicate marking ID')
        ids.add(row['id'])
    if not isinstance(p['artwork'],dict) or len(p['artwork'])>50:raise ValueError('Invalid artwork')
    for k,v in p['artwork'].items():
        if not isinstance(v,str) or len(v)>3_000_000:raise ValueError('圖檔太大')
        validate_png(base64.b64decode(v,validate=True))

DOMAINS=['EMC','Safety','Radio','Energy','Environmental','Other']
CONDITION_PRESETS={
 '此市場所有產品':None,
 '有數位電路':{'field':'digital','op':'eq','value':True},
 '有主動無線功能':{'any':[{'field':k,'op':'eq','value':True} for k in ['wifi','bluetooth','cellular']]+[{'field':'rfid','op':'in','value':['Reader/writer','Active tag']}]},
 'AC 或 AC/DC 供電':{'field':'power','op':'in','value':['AC','AC/DC']},
 '外接 PSU':{'field':'psu','op':'eq','value':'External'},
 'Class II':{'field':'safety_class','op':'eq','value':'II'},
 '有電池':{'field':'battery','op':'eq','value':True},
 '有雷射':{'field':'laser','op':'eq','value':True}}
DOMAIN_PRESETS={'EMC':'有數位電路','Safety':'此市場所有產品','Radio':'有主動無線功能','Energy':'此市場所有產品'}

def new_candidate(market,domain,name=None):
    from uuid import uuid4
    import copy
    return {'id':'M_'+uuid4().hex[:12],'title':name or domain+' marking（待建立）','markets':[market],
      'domains':[domain],'when':copy.deepcopy(CONDITION_PRESETS[DOMAIN_PRESETS.get(domain,'此市場所有產品')]),
      'kind':'task','content':'','reference':'','official_artwork_url':'','regulation':'',
      'note':'請確認此市場的標示要求、產品適用條件及圖檔。這是待建立項目，不會印到 Label。',
      'rule_status':'draft','last_reviewed_on':None,'default_include':False}

def make_project():
    import copy
    p=copy.deepcopy(DEFAULT)
    for market in p['market_catalog']:
        for row in load_label_rules()['items']:
            if market not in row['markets']:continue
            r=copy.deepcopy(row);r['id']=market+'_'+row['id'];r['markets']=[market]
            p['market_rules'].append(r)
        covered={d for r in p['market_rules'] if r['markets']==[market] for d in r['domains']}
        for domain in DOMAINS[:4]:
            if domain not in covered:p['market_rules'].append(new_candidate(market,domain))
    return p

def add_market(project,name,candidate_names=None):
    from uuid import uuid4
    name=name.strip()
    if not name or len(name)>40:raise ValueError('市場名稱需為 1–40 字元')
    if name.casefold() in {s.casefold() for s in project['market_catalog'].values()}:raise ValueError('此市場名稱已存在')
    if len(project['market_catalog'])>=30:raise ValueError('最多可設定 30 個市場')
    key='CUSTOM_'+uuid4().hex[:10]
    rows=[new_candidate(key,d,(candidate_names or {}).get(d,'').strip() or None) for d in DOMAINS[:4]]
    for row in rows:validate_rule(row,{**project['market_catalog'],key:name},custom=True)
    project['market_catalog'][key]=name;project['markets'].append(key)
    project['market_rules'].extend(rows)
    return key

def delete_market(project,key):
    if key not in project['market_catalog']:raise ValueError('市場不存在')
    project['market_catalog'].pop(key)
    project['markets']=[m for m in project['markets'] if m!=key]
    project['market_rules']=[r for r in project['market_rules'] if key not in r['markets']]
    used={r['content'] for r in project['market_rules'] if r['kind']=='symbol'}
    project['artwork']={k:v for k,v in project['artwork'].items() if k in used}

def update_market_rule(project,key,**updates):
    import copy
    row=next(r for r in project['market_rules'] if r['id']==key)
    candidate={**copy.deepcopy(row),**updates}
    validate_rule(candidate,project['market_catalog'],custom=True)
    if not candidate.get('domains') or not set(candidate['domains'])<=set(DOMAINS):raise ValueError('請選擇 marking 類別')
    for urlkey in ['official_artwork_url','reference']:
        value=candidate.get(urlkey,'')
        if value and not value.startswith(('https://','http://')):raise ValueError('來源網址須以 https:// 或 http:// 開頭')
    row.clear();row.update(candidate)

def select_items(project,pack=None):
    validate_project(project)
    rows=[]
    for row in project['market_rules']:
        markets=sorted(set(row['markets']) & set(project['markets']))
        if not markets:continue
        match,missing,trace=evaluate(row['when'],project['facts']) if row['when'] is not None else (True,[],{'operator':'market_rule','result':True})
        # Keep false / unknown candidates in the market inventory, but never print them.
        rendered=row['content'].format_map({'emc_class':project['facts']['emc_class'] or '[CLASS?]'}) if row.get('template_text') else row['content']
        item={**row,'matched_markets':markets,'match':match,'missing_fields':missing,'trace':trace,'render_text':rendered,'included':row['kind'] not in ['task'] and match is True}
        rows.append(item)
    # One physical symbol/text can serve multiple markets; retain their rule records.
    seen=set()
    for r in rows:
        if not r['included']:continue
        identity=(r['kind'],r['content'] if r['kind']=='symbol' else r['render_text'])
        if identity in seen:r['included']=False;r['duplicate_on_label']=True
        else:seen.add(identity)
    return rows

def font(size,bold=False):
    candidates=[Path('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc'),Path('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if bold else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for path in candidates:
        if path.exists():return ImageFont.truetype(str(path),max(1,int(size)))
    return ImageFont.load_default(size=max(1,int(size)))

def image_bytes(key,project):
    """Return monochrome image normalized for black/white label, preserving aspect."""
    override=project['artwork'].get(key)
    path=ROOT/'assets'/f'{key}.png'
    if not override and not path.exists():return None
    im=Image.open(io.BytesIO(base64.b64decode(override)) if override else path).convert('RGBA')
    # Black ink becomes foreground; white background becomes transparent.
    alpha=ImageChops.multiply(ImageOps.invert(im.convert('L')),im.getchannel('A'))
    bbox=alpha.getbbox()
    if not bbox:return None
    im=Image.new('RGBA',im.size,'white' if project['theme']=='dark' else 'black')
    im.putalpha(alpha);im=im.crop(bbox)
    out=io.BytesIO();im.save(out,format='PNG');return out.getvalue()

def make_layout(project,rows):
    W=1000;H=round(W*project['height_mm']/project['width_mm'])
    fg='#f7f7f4' if project['theme']=='dark' else '#111111'
    bg='#20201e' if project['theme']=='dark' else '#ffffff'
    elements=[]
    def text(x,y,s,size=23,bold=False):elements.append({'type':'text','x':x,'y':y,'text':s,'size':size,'bold':bold,'color':fg})
    def line(x1,y1,x2,y2):elements.append({'type':'line','xy':[x1,y1,x2,y2],'color':fg,'width':1})
    def block(x,y,s,width,size=23,bold=False):
        f=font(size,bold);current='';lines=[]
        for ch in s:
            if ch=='\n' or (current and f.getlength(current+ch)>width):lines.append(current);current='' if ch=='\n' else ch
            else:current+=ch
        if current:lines.append(current)
        for val in lines:text(x,y,val,size,bold);y+=size*1.4
        return y
    symbols=[r for r in rows if r['included'] and r['kind'] in ['symbol','placeholder']]
    texts=[r for r in rows if r['included'] and r['kind']=='text']
    left_width=500 if project['template']=='split' else 936
    y=30
    y=block(32,y,project['brand'],left_width,28,True)
    y=block(32,y,'Model: '+project['model'],left_width,27,True)
    y=block(32,y,project['description'],left_width,22)
    y+=7;line(32,y,32+left_width,y);y+=13
    power=project['facts']['power'] or '[AC/DC?]'
    input_text=f"Input: {project['voltage']} V {power}  {project['current']} A"
    if power in ['AC','AC/DC']:input_text+='  '+(project['frequency'].strip() or '[Hz?]')+' Hz'
    y=block(32,y,input_text,left_width,23)
    for r in texts:y=block(32,y,r['render_text'],left_width,21)
    y+=8
    y=block(32,y,'Made in '+project['origin'],left_width,21)
    if project['address']:y=block(32,y,project['address'],left_width,19)
    if project['template']=='split':
        sx,sy,area,cols=590,30,378,2
        line(558,30,558,H-68)
    else:sx,sy,area,cols=32,y+20,936,5
    cellw=area/cols;cellh=125
    for i,r in enumerate(symbols):
        x=sx+(i%cols)*cellw;yicon=sy+(i//cols)*cellh
        key=r['content']
        raw=image_bytes(key,project)
        if raw:
            im=Image.open(io.BytesIO(raw));iw,ih=im.size
            fit=min((cellw-25)/iw,82/ih)
            elements.append({'type':'image','x':x+(cellw-iw*fit)/2,'y':yicon,'w':iw*fit,'h':ih*fit,'data':base64.b64encode(raw).decode()})
        elif key=='class_ii':
            for off,size in [(0,66),(16,34)]:elements.append({'type':'rect','xy':[x+cellw/2-33+off,yicon+8+off,x+cellw/2-33+off+size,yicon+8+off+size],'color':fg,'width':4})
        elif key=='class_iii':
            cx=x+cellw/2
            for a,b in [((cx,yicon+3),(cx+40,yicon+43)),((cx+40,yicon+43),(cx,yicon+83)),((cx,yicon+83),(cx-40,yicon+43)),((cx-40,yicon+43),(cx,yicon+3))]:line(*a,*b);elements[-1]["width"]=4
            for offset in [-12,0,12]:line(cx+offset,yicon+27,cx+offset,yicon+59);elements[-1]["width"]=4
        else:
            elements.append({'type':'rect','xy':[x+9,yicon+7,x+cellw-9,yicon+78],'color':fg,'width':1})
            block(x+17,yicon+15,r['title'].upper(),cellw-34,16,True)
            text(x+17,yicon+54,'ARTWORK PENDING',11)
        caption={'class_ii':'CLASS II','class_iii':'CLASS III','ce':'CE','weee':'WEEE','rcm':'RCM'}.get(key,r['title'])
        caption_font=14
        while caption_font>9 and font(caption_font).getlength(caption)>cellw-24:caption_font-=1
        if font(caption_font).getlength(caption)>cellw-24:raise ValueError('Marking 名稱過長，請縮短名稱。')
        text(x+12,yicon+89,caption,caption_font)
    icon_end=sy+math.ceil(len(symbols)/cols)*cellh if symbols else 0
    used=max(y,icon_end) if project['template']=='split' else icon_end if symbols else y
    if used>H-75:raise ValueError('此尺寸放不下目前內容；請增加標籤高度、改用左文右圖，或縮短文字。沒有內容被裁掉。')
    line(32,H-57,968,H-57)
    text(32,H-43,'DRAFT / NOT FOR PRODUCTION — MARKS & APPLICABILITY TO VERIFY',15)
    return {'width':W,'height':H,'width_mm':project['width_mm'],'height_mm':project['height_mm'],'foreground':fg,'background':bg,'elements':elements}

def render_png(layout):
    scale=layout['width_mm']/25.4*300/layout['width']
    im=Image.new('RGB',(round(layout['width']*scale),round(layout['height']*scale)),layout['background']);d=ImageDraw.Draw(im)
    for e in layout['elements']:
        t=e['type']
        if t=='text':d.text((e['x']*scale,e['y']*scale),e['text'],font=font(e['size']*scale,e['bold']),fill=e['color'],anchor='lt')
        elif t=='line':d.line([x*scale for x in e['xy']],fill=e['color'],width=max(1,round(e['width']*scale)))
        elif t=='rect':d.rectangle([x*scale for x in e['xy']],outline=e['color'],width=max(1,round(e['width']*scale)))
        elif t=='image':
            icon=Image.open(io.BytesIO(base64.b64decode(e['data']))).convert('RGBA').resize((max(1,round(e['w']*scale)),max(1,round(e['h']*scale))),Image.Resampling.LANCZOS)
            im.paste(icon,(round(e['x']*scale),round(e['y']*scale)),icon)
    out=io.BytesIO();im.save(out,format='PNG',dpi=(300,300));return out.getvalue()

def render_svg(layout):
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout["width_mm"]}mm" height="{layout["height_mm"]}mm" viewBox="0 0 {layout["width"]} {layout["height"]}">','<title>Product label DRAFT — not for production</title>',f'<rect width="100%" height="100%" fill="{layout["background"]}"/>']
    for e in layout['elements']:
        t=e['type']
        if t=='text':parts.append(f'<text x="{e["x"]}" y="{e["y"]+e["size"]*.82}" font-family="Microsoft YaHei, DejaVu Sans, Arial, sans-serif" font-size="{e["size"]}" font-weight="{700 if e["bold"] else 400}" fill="{e["color"]}">{escape(e["text"])}</text>')
        elif t=='image':parts.append(f'<image x="{e["x"]}" y="{e["y"]}" width="{e["w"]}" height="{e["h"]}" href="data:image/png;base64,{e["data"]}"/>')
        elif t=='line':
            x1,y1,x2,y2=e['xy'];parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{e["color"]}" stroke-width="{e["width"]}"/>')
        elif t=='rect':
            x1,y1,x2,y2=e['xy'];parts.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" stroke="{e["color"]}" stroke-width="{e["width"]}" fill="none"/>')
    return '\n'.join(parts+['</svg>'])
