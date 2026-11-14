"""Matched-date healthcare comparison."""
import pathlib,re,subprocess
root=pathlib.Path(__file__).parent
s=(root/'terminal_template.html').read_text()
helper=s[s.index('function healthcareComparison('):s.index('function renderMain(){')]
script='const assert=require("assert/strict");\n'+helper+'''
const c=healthcareComparison([{date:'2021-01-01',v:50},{date:'2021-01-04',v:100},{date:'2024-01-04',v:150}], [{date:'2021-01-04',v:200},{date:'2024-01-04',v:240}]);
assert.equal(c.start,'2021-01-04');assert.equal(c.a.at(-1).v,50);assert.ok(Math.abs(c.b.at(-1).v-20)<1e-10);
assert.equal(healthcareComparison([{date:'2021-01-01',v:1}],[{date:'2021-01-02',v:1}]),null);
'''
subprocess.run(['node','-e',script],check=True)
print('Healthcare comparator uses identical dates and a common starting basis')
