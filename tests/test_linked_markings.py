import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from compliance.manual_catalog import make_project,select_items,add_feature,delete_feature
from compliance.linked_markings import active_radios,linked_items
from compliance.label_designer import make_layout,render_png

def contents(p):return [r['content'] for r in select_items(p) if r['included']]
def get(items,label):return next(x for x in items if x.label==label)

@pytest.mark.parametrize('cls,value',[('I',None),('II','class_ii'),('III','class_iii'),(None,None)])
def test_safety_class(cls,value):
 p=make_project();p['markets']=[];p['facts']['safety_class']=cls
 assert contents(p)==([value] if value else [])
 assert not any('CLASS' in r['id'] for r in p['market_rules'])
 assert render_png(make_layout(p,select_items(p))).startswith(b'\x89PNG')
 if cls=='III':assert not any('PENDING' in e.get('text','') for e in make_layout(p,select_items(p))['elements'])

def test_canada_emc():
 p=make_project()
 assert 'CAN ICES-003(A) / NMB-003(A)' in contents(p)
 p['facts']['emc_class']='B'
 assert 'CAN ICES-003(B) / NMB-003(B)' in contents(p)
 assert not any('(A)' in c for c in contents(p))
 p['markets'].remove('CA');assert not any('ICES' in c for c in contents(p))
 p['markets'].append('CA');p['facts']['emc_class']=None
 assert not any('ICES' in c for c in contents(p))
 assert not any('ICES' in r['id'] for r in p['market_rules'])

def test_rf_markets_modes_and_dedup():
 p=make_project();ids={'fcc_id':'TEST123','ic_id':'12345-TEST','mode':'module'}
 p['radio_ids']={'shared':dict(ids)}
 assert not any('ID:' in c or 'IC:' in c for c in contents(p))
 p['facts'].update(wifi=True,bluetooth=True)
 assert contents(p).count('Contains FCC ID: TEST123')==1
 assert contents(p).count('Contains IC: 12345-TEST')==1
 p['markets']=['CA'];assert not any('FCC' in c for c in contents(p))
 p['facts']['bluetooth']=False;p['radio_ids']['shared']['mode']='device'
 assert 'IC: 12345-TEST' in contents(p)
 p['facts']['wifi']=False
 assert not any('IC:' in c for c in contents(p))
 p['facts']['rfid']='Passive tag only';assert not active_radios(p)
 p['facts']['rfid']='Reader/writer';assert active_radios(p)==[('rfid','RFID / NFC')]

def test_custom_rf():
 p=make_project();key=add_feature(p,'Zigbee',True);f=p['custom_features'][0]
 p['radio_ids']['shared']={'fcc_id':'TEST456','ic_id':'','mode':'device'}
 assert not active_radios(p)
 f['selected']=True;assert 'FCC ID: TEST456' in contents(p)
 f['is_rf']=False;assert 'FCC ID: TEST456' not in contents(p)
 with pytest.raises(ValueError):add_feature(p,'Zigbee')
 delete_feature(p,key);assert p['radio_ids']['shared']['fcc_id']=='TEST456'

def test_ui_links_and_custom_feature():
 at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
 assert not at.exception and not at.error
 assert not any(x.label in ['電池','雷射'] for x in at.checkbox)
 get(at.selectbox,'整機保護類別').set_value('III').run()
 get(at.selectbox,'EMC Class').set_value('B').run()
 assert 'class_iii' in contents(at.session_state.label_project)
 assert 'CAN ICES-003(B) / NMB-003(B)' in contents(at.session_state.label_project)
 get(at.checkbox,'Wi-Fi').check().run()
 get(at.text_input,'FCC ID').set_value('TEST123');get(at.text_input,'IC ID').set_value('12345-TEST').run()
 assert 'FCC ID: TEST123' in contents(at.session_state.label_project)
 get(at.checkbox,'Wi-Fi').uncheck().run()
 assert 'FCC ID: TEST123' not in contents(at.session_state.label_project)
 get(at.checkbox,'Wi-Fi').check().run()
 assert get(at.text_input,'FCC ID').value=='TEST123'
 get(at.checkbox,'Wi-Fi').uncheck().run()
 get(at.text_input,'功能名稱').set_value('Zigbee')
 get(at.checkbox,'此功能具有 RF 發射功能（連動 FCC ID／IC ID）').check()
 get(at.button,'新增功能').click().run()
 get(at.checkbox,'Zigbee（RF）').check().run()
 get(at.text_input,'FCC ID').set_value('TEST456').run()
 assert 'FCC ID: TEST456' in contents(at.session_state.label_project)
 key=at.session_state.label_project['custom_features'][0]['id']
 get(at.multiselect,'刪除自訂功能').set_value([key]).run()
 get(at.button,'刪除所選功能').click().run()
 assert not at.exception and not at.error
 assert 'FCC ID: TEST456' not in contents(at.session_state.label_project)
