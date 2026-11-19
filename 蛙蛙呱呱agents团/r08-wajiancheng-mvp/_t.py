import sys, json
sys.path.insert(0,'.')
import agent
print('skills', sorted(agent.SKILL_BY_NAME)[:20] if hasattr(agent,'SKILL_BY_NAME') else 'n/a')
try:
    print('route', agent._route('帮我做一个 html 报告页'))
except Exception as e:
    print('route err', type(e).__name__, e)
