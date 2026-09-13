"""Versioned, self-contained project files. No filesystem paths or executable data."""
import json
from .manual_catalog import validate_project

FORMAT='product-label-designer'
VERSION=1
MAX_BYTES=150*1024*1024

def dump_project(project):
    validate_project(project)
    raw=json.dumps({'format':FORMAT,'version':VERSION,'project':project},ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')
    if len(raw)>MAX_BYTES:raise ValueError('專案檔超過 150 MB，請減少圖檔')
    return raw

def _unique_object(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:raise ValueError('專案包含重複欄位')
        obj[key]=value
    return obj

def load_project(raw):
    if len(raw)>MAX_BYTES:raise ValueError('專案檔上限為 150 MB')
    try:
        doc=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=_unique_object)
        if not isinstance(doc,dict) or set(doc)!={'format','version','project'} or doc['format']!=FORMAT:raise ValueError('不是 Product Label Designer 專案檔')
        if type(doc['version']) is not int or doc['version']!=VERSION:raise ValueError('不支援此專案版本')
        validate_project(doc['project'])
        return doc['project']
    except (UnicodeError,TypeError,KeyError,AttributeError,RecursionError,OverflowError) as exc:
        raise ValueError('專案檔格式錯誤，無法讀取') from exc
