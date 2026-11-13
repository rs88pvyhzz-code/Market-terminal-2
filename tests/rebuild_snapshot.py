"""Apply the current frontend to an archived payload without fetching new data."""
import json,re,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_terminal import assemble_frontend
from build_site import inject_layout
source=next(Path(sys.argv[1]).rglob('terminal.html')).read_text()
def payload(html):
    start=re.search(r'window.MT_DATA\s*=\s*',html).end()
    return json.JSONDecoder().raw_decode(html[start:])[0]
data=payload(source)
assert not data.get('demo')
out=Path(sys.argv[2])
frontend=assemble_frontend(Path('terminal_template.html').read_text())
out.write_text(frontend.replace('/*__DATA__*/null',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')))
subprocess.run([sys.executable,'terminal_research_upgrade.py',str(out)],check=True)
subprocess.run([sys.executable,'market_terminal_cleanup.py','--post','--html',str(out)],check=True)
inject_layout(out)
assert payload(out.read_text())==data
print('PASS: archived production payload unchanged')
