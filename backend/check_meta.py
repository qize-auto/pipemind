import sys
sys.stdout.reconfigure(encoding='utf-8')
import chromadb, json
from chromadb.config import Settings
import os

base = os.path.expanduser('~/.mempalace/palace')
c = chromadb.PersistentClient(path=base, settings=Settings(anonymized_telemetry=False))

for coll in c.list_collections():
    cnt = coll.count()
    if cnt > 0:
        r = coll.get(limit=2)
        print(f'Collection: {coll.name} ({cnt} docs)')
        if r and r['metadatas']:
            print(f'  meta keys: {list(r["metadatas"][0].keys())}')
            print(f'  example: {json.dumps(r["metadatas"][0], indent=2, ensure_ascii=False, default=str)[:600]}')
        if r and r['documents']:
            print(f'  doc[0][:100]: {r["documents"][0][:100]}')
        break
