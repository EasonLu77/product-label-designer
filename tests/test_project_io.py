import copy,io,json
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image,ImageDraw
from streamlit.testing.v1 import AppTest
from compliance.manual_catalog import make_project,add_market,add_feature,save_marking,select_items
from compliance.project_io import dump_project,load_project
from compliance.label_designer import render_png,make_layout

def get(items,label):return next(x for x in items if x.label==label)
def project():
 p=make_project();m=add_market(p,'Test Market');p['brand']='Saved Brand'
 f=add_feature(p,'Zigbee',True);p['custom_features'][0]['selected']=True
 p['radio_ids']['shared']={'mode':'module','fcc_id':'TEST123','ic_id':'12345-TEST'}
 im=Image.new('RGBA',(40,40),'white');ImageDraw.Draw(im).rectangle((5,5,30,30),fill='black')
 buf=io.BytesIO();im.save(buf,format='PNG')
 key=save_marking(p,m,title='Saved icon',domains=['RF','EMC'],kind='symbol',png=buf.getvalue(),official_artwork_url='https://example.org/icon.png',regulation='Test reference')
 next(r for r in p['market_rules'] if r['id']==key)['selected']=True
 return p

def test_round_trip():
 p=project();loaded=load_project(dump_project(p))
 assert loaded==p
 assert render_png(make_layout(p,select_items(p)))==render_png(make_layout(loaded,select_items(loaded)))
 loaded['brand']='Independent';assert p['brand']=='Saved Brand'

@pytest.mark.parametrize('mutation',[
 lambda d:d.update(version=999),
 lambda d:d['project']['custom_features'].append(copy.deepcopy(d['project']['custom_features'][0])),
 lambda d:d['project']['market_rules'][0].update(domains=['Unknown']),
 lambda d:d['project'].update(width_mm=float('nan')),
 lambda d:d['project']['radio_ids'].update(wifi={}),
 lambda d:d['project']['market_rules'][0].update(content='../../secret',kind='symbol'),
 lambda d:d['project']['artwork'].update(invalid='bad'),
])
def test_invalid_project(mutation):
 d=json.loads(dump_project(project()));mutation(d)
 with pytest.raises(ValueError):load_project(json.dumps(d).encode())

@pytest.mark.parametrize('raw',[b'not json',b'[]',b'{"format":"a","format":"b"}',b'\xff'])
def test_invalid_file(raw):
 with pytest.raises(ValueError):load_project(raw)

def test_single_ids_and_collapsible_grid():
 at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
 assert not at.exception and not at.error
 assert get(at.expander,'② 功能規格').proto.expanded is False
 get(at.checkbox,'Wi-Fi').check().run();get(at.checkbox,'Bluetooth').check().run()
 assert len([x for x in at.text_input if x.label=='FCC ID'])==1
 assert len([x for x in at.text_input if x.label=='IC ID'])==1
 get(at.text_input,'FCC ID').set_value('COMMON').run()
 get(at.checkbox,'Wi-Fi').uncheck().run()
 assert get(at.text_input,'FCC ID').value=='COMMON'
 for name in ['Feature One','Feature Two']:
  get(at.text_input,'功能名稱').set_value(name);get(at.button,'新增功能').click().run()
 columns=at.get('column')
 assert any(any(x.label=='Feature One' for x in c.checkbox) and not any(x.label=='Feature Two' for x in c.checkbox) for c in columns)
 assert any(any(x.label=='Feature Two' for x in c.checkbox) and not any(x.label=='Feature One' for x in c.checkbox) for c in columns)
 assert get(at.get('download_button'),'儲存專案')

def test_ui_load_and_bad_file_preserves_current_project():
 app=str(Path(__file__).resolve().parents[1]/'app.py')
 p=project();raw=dump_project(p)
 def uploader(label,*args,**kwargs):return io.BytesIO(raw) if label=='選擇專案檔（JSON）' else None
 with patch('streamlit.file_uploader',side_effect=uploader):
  at=AppTest.from_file(app,default_timeout=30).run()
  get(at.text_input,'公司／品牌').set_value('Unsaved Brand').run()
  get(at.button,'讀取專案').click().run()
  assert not at.exception and not at.error
  assert at.session_state.label_project==p
  assert get(at.text_input,'公司／品牌').value=='Saved Brand'
  assert get(at.text_input,'FCC ID').value=='TEST123'
  assert get(at.checkbox,'Zigbee（RF）').value
  assert get(at.checkbox,'Saved icon · RF, EMC').value
  before=copy.deepcopy(at.session_state.label_project);raw=b'broken json'
  get(at.button,'讀取專案').click().run()
  assert not at.exception and at.error
  assert at.session_state.label_project==before
