"""
mempalace_server.py — Persistent MemPalace search daemon (v2)
Uses mempalace's internal search API + direct ChromaDB access.
"""
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')
os.environ['ANONYMIZED_TELEMETRY'] = 'NO'

PALACE_DIR = os.path.expanduser('~/.mempalace/palace')

try:
    import chromadb
    from chromadb.config import Settings

    # Direct ChromaDB connection (no sentence-transformers needed)
    client = chromadb.PersistentClient(
        path=PALACE_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    collections = client.list_collections()
    coll_map = {c.name: c for c in collections}

    def search_collection(coll, query_text, n_results=3):
        """Search using ChromaDB's default embedding"""
        try:
            results = coll.query(
                query_texts=[query_text],
                n_results=min(n_results, coll.count() or 1)
            )
            return results
        except Exception as e:
            return {'error': str(e)}

    # Ready signal
    print(json.dumps({
        'type': 'ready',
        'collections': list(coll_map.keys()),
        'count': len(collections),
        'palace': PALACE_DIR
    }), flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            if req.get('_ping'):
                continue  # keep-alive ping, no reply

            query = req.get('query', '')
            n_results = min(req.get('n_results', 3), 20)
            wing = req.get('wing', '').lower()
            room = req.get('room', '').lower()

            if not query:
                print(json.dumps({'type': 'error', 'message': 'query required'}), flush=True)
                continue

            # Pick target collections
            target = []
            for name, coll in coll_map.items():
                nlower = name.lower()
                if wing and wing not in nlower:
                    continue
                if room and room not in nlower:
                    continue
                target.append((name, coll))

            all_results = []
            for name, coll in target:
                hits = search_collection(coll, query, n_results)
                if hits and 'error' not in hits:
                    ids = hits.get('ids', [[]])[0]
                    dists = hits.get('distances', [[]])[0]
                    metas = hits.get('metadatas', [[]])[0]
                    docs = hits.get('documents', [[]])[0]

                    for i in range(len(ids)):
                        meta = metas[i] if metas and i < len(metas) else {}
                        doc = docs[i] if docs and i < len(docs) else ''
                        # Extract filename from source_file
                        src = meta.get('source_file', '')
                        if '\\' in src:
                            src = src.rsplit('\\', 1)[-1]  # Windows
                        elif '/' in src:
                            src = src.rsplit('/', 1)[-1]  # Unix
                        # Content snippet: prefer doc, then fallback to metadata
                        snippet = doc or meta.get('content', '') or meta.get('text', '')
                        all_results.append({
                            'id': ids[i],
                            'score': 1.0 - dists[i] if dists and i < len(dists) else 0,
                            'source': src or name,
                            'room': meta.get('room', name),
                            'wing': meta.get('wing', 'workspace'),
                            'snippet': snippet[:400],
                        })

            all_results.sort(key=lambda x: x['score'], reverse=True)
            all_results = all_results[:n_results]

            print(json.dumps({
                'type': 'results',
                'query': query,
                'count': len(all_results),
                'results': all_results
            }), flush=True)

        except json.JSONDecodeError:
            print(json.dumps({'type': 'error', 'message': 'invalid JSON'}), flush=True)
        except Exception as e:
            print(json.dumps({'type': 'error', 'message': str(e)}), flush=True)

except Exception as e:
    print(json.dumps({'type': 'fatal', 'error': str(e)}), flush=True)
    sys.exit(1)
