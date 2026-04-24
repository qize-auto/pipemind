#!/usr/bin/env python3
"""
MemPalace bridge for PipeMind.
Called by Node.js subprocess with JSON stdin/stdout.
Usage: echo '{"action":"search","query":"...","wing":"pipemind","n_results":5}' | python mempalace_bridge.py
       echo '{"action":"save","wing":"pipemind","room":"default","content":"..."}' | python mempalace_bridge.py
"""
import sys, json, os

# Set proxy for model download
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7897')
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7897')

def handle(req):
    action = req.get('action', 'search')

    if action == 'search':
        from mempalace.searcher import search_memories
        results = search_memories(
            query=req['query'],
            palace_path=req.get('palace_path', os.path.expanduser('~/.mempalace/palace')),
            wing=req.get('wing'),
            room=req.get('room'),
            n_results=req.get('n_results', 5),
            max_distance=req.get('max_distance', 1.5),
        )
        return {'success': True, 'data': results}

    elif action == 'save':
        import chromadb
        from mempalace.config import MempalaceConfig
        from mempalace.mcp_server import tool_add_drawer
        # Validate wing/room first
        wing = req.get('wing')
        room = req.get('room')
        content = req.get('content')
        if not all([wing, room, content]):
            return {'success': False, 'error': 'wing, room, and content required'}
        result = tool_add_drawer(
            wing=wing,
            room=room,
            content=content,
            source_file=req.get('source_file', 'pipemind'),
            added_by='pipemind'
        )
        return {'success': True, 'data': result}

    elif action == 'list_wings':
        from mempalace.mcp_server import tool_list_wings
        result = tool_list_wings()
        return {'success': True, 'data': result}

    elif action == 'list_rooms':
        from mempalace.mcp_server import tool_list_rooms
        result = tool_list_rooms(wing=req.get('wing'))
        return {'success': True, 'data': result}

    elif action == 'status':
        from mempalace.mcp_server import tool_status
        result = tool_status()
        return {'success': True, 'data': result}

    else:
        return {'success': False, 'error': f'Unknown action: {action}'}

if __name__ == '__main__':
    try:
        req = json.loads(sys.stdin.read())
        result = handle(req)
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False))
