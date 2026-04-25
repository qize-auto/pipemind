import sys
sys.stdout.reconfigure(encoding='utf-8')
import chromadb, json
from chromadb.config import Settings
import os

base = os.path.expanduser('~/.mempalace/palace')
c = chromadb.PersistentClient(path=base, settings=Settings(anonymized_telemetry=False))

for coll in c.list_collections():
    if 'drawer' in coll.name.lower():
        cnt = coll.count()
        r = coll.get(limit=2)
        print(f'Collection: {coll.name} ({cnt} docs)')
        if r and r['metadatas']:
            print(f'  meta keys: {list(r["metadatas"][0].keys())}')
            print(f'  example meta: {json.dumps(r["metadatas"][0], indent=2, ensure_ascii=False, default=str)[:800]}')
        if r and r['documents']:
            print(f'  doc[0][:150]: {r["documents"][0][:150]}')
        break
