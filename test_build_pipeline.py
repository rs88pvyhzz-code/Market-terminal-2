"""Build pipeline guards: front-end manifest, CSS scope aliases, layout injection."""
import re
import tempfile
import unittest
from pathlib import Path

import build_site
import build_terminal


class Manifest(unittest.TestCase):
    def test_every_listed_asset_exists(self):
        for name in build_terminal.FRONTEND_EARLY_JS + build_terminal.FRONTEND_LATE_JS + [f for _, f in build_terminal.FRONTEND_CSS]:
            self.assertTrue((build_terminal.ROOT / name).is_file(), name)
        for name in (build_site.LAYOUT_CSS, build_site.LAYOUT_JS):
            self.assertTrue((build_site.ROOT / name).is_file(), name)

    def test_missing_insertion_point_stops_the_build(self):
        with self.assertRaises(SystemExit):
            build_terminal.assemble_frontend('<html><head></head><body>no markers</body></html>')


class ScopeAliases(unittest.TestCase):
    def test_original_rules_are_untouched(self):
        css = ('.a{x:y}@media(max-width:600px){#gilts .row h3{c:d}.b{e:f}}'
               '#etf-tracker-panel .etf-detail h3,#etf-tracker-panel{g:h}.x:not(.panel) h3{i:j}.panel{k:l}')
        out = build_site.add_scope_aliases(css)
        stripped = re.sub(r',\.scope-[^,{]*|,#etf-tracker-panel \.scope-etf-detail h3', '', out)
        self.assertEqual(stripped, css)

    def test_aliases_only_for_ancestor_scopes(self):
        out = build_site.add_scope_aliases('#gilts .row{a:b}#gilts{c:d}.x:not(.panel) h3{e:f}')
        self.assertIn('.scope-gilts .row', out)
        self.assertNotIn('.scope-gilts{', out)          # the panel itself is not aliased
        self.assertNotIn('not(.scope-panel)', out)      # never inside :not()

    def test_brace_balance_on_real_stylesheets(self):
        for name in [f for _, f in build_terminal.FRONTEND_CSS]:
            css = (build_terminal.ROOT / name).read_text('utf-8')
            out = build_site.add_scope_aliases(css)
            self.assertEqual(out.count('{'), css.count('{'), name)
            self.assertEqual(out.count('}'), css.count('}'), name)


class LayoutInjection(unittest.TestCase):
    def page(self):
        return ('<html><head><style>#gilts .r{a:b}</style></head><body><script>window.MT_DATA = {"news":[]};</script>'
                '<script>\'use strict\';(function(){\n'
                'function init(){}\ninit();\n})();</script></body></html>')

    def test_injected_inside_application_scope_once(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 't.html'
            f.write_text(self.page())
            build_site.inject_layout(f)
            first = f.read_text()
            build_site.inject_layout(f)                 # idempotent
            self.assertEqual(first, f.read_text())
            body = first[first.index("'use strict'"):]
            self.assertLess(body.index('init();'), body.index('terminal-layout-script'))
            self.assertLess(body.index('terminal-layout-script'), body.rindex('})();'))
            self.assertIn('.scope-gilts .r', first)
            self.assertLess(first.index('window.MT_DATA'), first.index('id="news-freshness"'))
            self.assertLess(first.index('id="news-freshness"'), first.index("'use strict'"))

    def test_missing_scope_end_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 't.html'
            f.write_text('<html><head></head><body><script>window.MT_DATA = {};</script></body></html>')
            with self.assertRaises(SystemExit):
                build_site.inject_layout(f)


if __name__ == '__main__':
    unittest.main()
