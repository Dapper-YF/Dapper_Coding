# -*- coding: utf-8 -*-
import os, json

sessions_dir = r'C:\Users\Dapper\.openclaw\agents\agent-architect\sessions'
sj_path = os.path.join(sessions_dir, 'sessions.json')

with open(sj_path, 'r', encoding='utf-8') as f:
    sessions = json.load(f)

# Protected keys (never delete these)
protected = {'agent:agent-architect:main', 'agent:agent-architect:feishu:direct:ou_1aca7f5ef53efac38e6c9f67c27cf949'}

# Find done subagent sessions to delete
to_delete_keys = []
for key in sessions:
    if any(x in key for x in protected):
        continue
    if 'subagent:' in key:
        status = sessions[key].get('status', '') if isinstance(sessions[key], dict) else ''
        if status == 'done':
            to_delete_keys.append(key)

print(f'Sessions to delete: {len(to_delete_keys)}')
for k in to_delete_keys:
    print(f'  {k}')

# Count total before
all_keys = list(sessions.keys())
subagent_keys = [k for k in all_keys if 'subagent:' in k and not any(x in k for x in protected)]
print(f'\nTotal subagent sessions: {len(subagent_keys)} (threshold: 10)')

if len(subagent_keys) > 10 and to_delete_keys:
    # Delete .jsonl files
    for key in to_delete_keys:
        # Get sessionId from sessions.json
        session_data = sessions[key]
        if isinstance(session_data, dict):
            session_id = session_data.get('sessionId', '')
            if session_id:
                jsonl_path = os.path.join(sessions_dir, f'{session_id}.jsonl')
                if os.path.exists(jsonl_path):
                    os.remove(jsonl_path)
                    print(f'Deleted: {jsonl_path}')
                else:
                    print(f'Not found: {jsonl_path}')
        
        # Remove from sessions.json
        del sessions[key]
    
    # Write updated sessions.json
    with open(sj_path, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
    
    print(f'\nCleaned {len(to_delete_keys)} sessions. Remaining subagent sessions: {len([k for k in sessions if "subagent:" in k and not any(x in k for x in protected)])}')
else:
    print('No cleanup needed (threshold not reached)')
