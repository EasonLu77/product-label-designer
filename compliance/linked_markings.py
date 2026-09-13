"""Only the user-requested links; all other catalog markings remain manual."""
from .engine import ROOT,read_json

def active_radios(p):
    radios=[(key,name) for key,name in [('wifi','Wi-Fi'),('bluetooth','Bluetooth'),('cellular','Cellular')] if p['facts'][key]]
    if p['facts']['rfid'] in ['Reader/writer','Active tag']:radios.append(('rfid','RFID / NFC'))
    radios.extend((r['id'],r['name']) for r in p['custom_features'] if r['selected'] and r['is_rf'])
    return radios

def linked_items(p):
    config=read_json(ROOT/'data/linked_markings.json');rows=[]
    def add(key,title,kind,content,reference,note=''):
        rows.append(dict(id='AUTO_'+key,title=title,kind=kind,content=content,reference=reference,note=note))
    safety=config['safety'].get(p['facts']['safety_class'])
    if safety:add('SAFETY',**safety)
    emc=config['emc'];cls=p['facts']['emc_class']
    if emc['market'] in p['markets'] and cls in ['A','B']:
        add('EMC_CA','Canada ICES Class '+cls,'text',emc['template'].format(emc_class=cls),emc['reference'],emc['note'])
    if active_radios(p):
        ids=p['radio_ids']['shared']
        for rule in config['radio']:
            value=ids.get(rule['field'],'').strip()
            if rule['market'] in p['markets'] and value:
                prefix=rule['module_prefix'] if ids.get('mode')=='module' else rule['prefix']
                add('SHARED_'+rule['field'],'共用 '+rule['field'],'text',prefix+value,rule['reference'])
    return rows
