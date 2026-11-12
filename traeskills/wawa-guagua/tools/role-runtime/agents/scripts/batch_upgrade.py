# -*- coding: utf-8 -*-
import os, re
agents_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for i in range(2, 21):
    rid = f'r{i:02d}'
    matched = [d for d in os.listdir(agents_dir) if d.startswith(rid)][0]
    agent_py = os.path.join(agents_dir, matched, 'agent.py')
    with open(agent_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'chat' in content: continue
        
    new_content = content.replace('import sys', 'import sys\nfrom agents.shared.chat_cli import add_chat_parser, handle_chat')
    
    # regex sub for subparsers
    new_content = re.sub(r'subparsers = parser\.add_subparsers\(dest="cmd", required=True\)', 
                         'subparsers = parser.add_subparsers(dest="cmd", required=True)\n    add_chat_parser(subparsers)', 
                         new_content)
    
    handle_chat_logic = f'''
    if args.cmd == "chat":
        return handle_chat(args, role_id="{rid}")
'''
    new_content = new_content.replace('    if args.cmd == "manifest":', handle_chat_logic + '    if args.cmd == "manifest":')
    
    with open(agent_py, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Upgraded {rid}')
