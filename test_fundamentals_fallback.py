import unittest
import market_fundamentals as m


class FillMissing(unittest.TestCase):
    def test_fills_only_when_today_is_empty(self):
        companies=[{'symbol':'SHEL.L','marketCap':None,'trailingPE':None,'fundamentalSource':'Yahoo'},
                   {'symbol':'SKWD','marketCap':2.5e9,'trailingPE':14.0}]
        saved=[{'symbol':'SHEL.L','asOf':'2026-11-12T08:00:00+00:00','marketCap':2.1e11,'trailingPE':12.3},
               {'symbol':'SKWD','asOf':'2026-11-01','marketCap':9e9,'trailingPE':99}]
        self.assertEqual(m.fill_missing(companies,saved),['SHEL.L'])
        self.assertEqual(companies[0]['trailingPE'],12.3)
        self.assertEqual(companies[0]['fundamentalsRetainedFrom'],'2026-11-12')
        self.assertIn('retained from 2026-11-12',companies[0]['fundamentalSource'])
        self.assertEqual(companies[1]['trailingPE'],14.0)

    def test_nothing_saved_leaves_blank(self):
        companies=[{'symbol':'X','marketCap':None}]
        self.assertEqual(m.fill_missing(companies,[]),[])
        self.assertIsNone(companies[0]['marketCap'])


if __name__=='__main__':
    unittest.main()
