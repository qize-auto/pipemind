#!/usr/bin/env python3
"""
MemPalace bridge for PipeMind.
Reads JSON from first argument (or stdin fallback).
Usage: python bridge.py '{"action":"search","query":"..."}'
"""
import sys, json, os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
os.environ.setdefault('HTTP_PROXY', 'http://127.0.0.1:7897')
os.environ.setdefault('HTTPS_PROXY', 'http://127.0.0.1:7897')

PALACE = os.path.expanduser('~/.mempalace/palace')


def handle(req):
    action = req.get('action', 'search')

    if action == 'search':
        from mempalace.searcher import search_memories
        results = search_memories(
            query=req['query'],
            palace_path=PALACE,
            wing=req.get('wing'),
            room=req.get('room'),
            n_results=req.get('n_results', 5),
            max_distance=req.get('max_distance', 1.5),
        )
        # Normalize: search_memories returns {results: [{text:..., ...}]}
        return {'success': True, 'data': results}

    elif action == 'status':
        from mempalace.mcp_server import tool_status
        return {'success': True, 'data': tool_status()}

    elif action == 'list_wings':
        from mempalace.mcp_server import tool_list_wings
        return {'success': True, 'data': tool_list_wings()}

    elif action == 'list_rooms':
        from mempalace.mcp_server import tool_list_rooms
        return {'success': True, 'data': tool_list_rooms(wing=req.get('wing', 'workspace'))}

    elif action == 'save':
        from mempalace.mcp_server import tool_add_drawer
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

    else:
        return {'success': False, 'error': f'Unknown action: {action}'}


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            arg = sys.argv[1]
            # If arg is a file path, read it
            if os.path.isfile(arg):
                with open(arg, 'r', encoding='utf-8') as f:
                    req = json.loads(f.read())
            else:
                req = json.loads(arg)
        else:
            req = json.loads(sys.stdin.read())
        result = handle(req)
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({'success': False, 'error': f'{type(e).__name__}: {e}'}, ensure_ascii=False))
