import copy,io
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
from streamlit.testing.v1 import AppTest
from compliance.manual_catalog import make_project,add_market,delete_market,save_marking,delete_marking,select_items
from compliance.label_designer import render_png,make_layout

def add(p,m,**kw):return save_marking(p,m,title='Test mark',domains=['EMC','RF'],kind='text',content='TEST MARK',**kw)
def included(p):return [r for r in select_items(p) if r['included'] and not r.get('automatic')]
def get(items,label):return next(x for x in items if x.label==label)

def test_manual_selection():
 p=make_project();m=add_market(p,'Japan')
 assert not any(m in r['markets'] for r in p['market_rules'])
 key=add(p,m);r=next(r for r in p['market_rules'] if r['id']==key)
 assert not included(p)
 r['selected']=True;assert len(included(p))==1
 baseline=render_png(make_layout(p,select_items(p)))
 p['facts'].update(wifi=True,bluetooth=True,cellular=True,laser=True,battery=True,category='Other',rfid='Reader/writer')
 assert render_png(make_layout(p,select_items(p)))==baseline
 p['markets'].remove(m);assert not included(p)
 p['markets'].append(m);assert len(included(p))==1
 r['selected']=False;assert not included(p)

def test_dedup_validation():
 p=make_project();m=add_market(p,'Test');a=add(p,m);b=add(p,'US')
 for r in p['market_rules']:r['selected']=r['id'] in [a,b]
 assert len(included(p))==1
 delete_market(p,m);assert len(included(p))==1
 delete_marking(p,b);assert not included(p)
 before=copy.deepcopy(p)
 with pytest.raises(ValueError):save_marking(p,'US',title='Bad',domains=[],kind='text',content='bad')
 with pytest.raises(ValueError):add(p,'US',official_artwork_url='javascript:bad')
 assert p==before

def test_png():
 p=make_project();im=Image.new('RGBA',(50,50),'white');ImageDraw.Draw(im).rectangle((10,10,40,40),fill='black')
 out=io.BytesIO();im.save(out,format='PNG')
 key=save_marking(p,'US',title='Icon',domains=['Safety'],kind='symbol',png=out.getvalue())
 row=next(r for r in p['market_rules'] if r['id']==key);row['selected']=True
 assert any(e['type']=='image' for e in make_layout(p,select_items(p))['elements'])
 save_marking(p,'US',key=key,title='Edited',domains=['Safety','RF'],kind='symbol')
 assert row['selected'] and row['title']=='Edited'
 delete_marking(p,key);assert not p['artwork']

def test_ui():
 at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
 assert not at.exception and not at.error
 get(at.text_input,'市場名稱').set_value('Japan');get(at.button,'新增市場').click().run()
 assert not at.exception and not at.error
 m=next(k for k,v in at.session_state.label_project['market_catalog'].items() if v=='Japan')
 form=next(f for f in at.get('form') if f.proto.form.form_id=='marking_'+m)
 get(form.text_input,'Marking 名稱').set_value('My marking')
 get(form.multiselect,'Requirement 分類').set_value(['EMC','RF'])
 get(form.selectbox,'標示類型').set_value('text')
 get(form.text_area,'Label 文字（文字類型使用）').set_value('MY MARK')
 get(form.button,'新增 marking').click().run()
 assert not at.exception and not at.error
 get(at.checkbox,'My marking · EMC, RF').check().run()
 assert len(included(at.session_state.label_project))==1
 get(at.checkbox,'Wi-Fi').check().run();assert len(included(at.session_state.label_project))==1
 get(at.checkbox,'My marking · EMC, RF').uncheck().run();assert not included(at.session_state.label_project)
 get(at.multiselect,'選擇要刪除的市場').set_value([m]).run();get(at.button,'刪除所選市場').click().run()
 assert not at.exception and not at.error
 assert m not in at.session_state.label_project['market_catalog']
