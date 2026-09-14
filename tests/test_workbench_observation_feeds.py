import importlib.util,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class PublicFeedTests(unittest.TestCase):
 def setUp(self): self.data=json.loads((ROOT/'a-share-workbench/observation-feeds.json').read_text())
 def test_selected_only(self):
  for key in ('a','m'):
   rows=self.data[key]['rows'];self.assertLessEqual(sum(r["in_futu"] for r in rows),10);self.assertEqual(len(rows),len({x['code'] for x in rows}));self.assertTrue(self.data[key]['verified'])
 def test_privacy_allowlist(self):
  allowed={'code','name','label','kind','pivot_time','bar_end','price','detected_at','market','replacement','delivery'}
  for row in self.data['cl20']['rows']: self.assertEqual(set(row),allowed)
  raw=json.dumps(self.data);self.assertNotIn('/Users/',raw);self.assertNotIn('message_id',raw);self.assertNotIn('acc_id',raw)
 def test_lifecycle_and_order(self):
  rows=self.data['cl20']['rows'];dates=[r['detected_at'] for r in rows];self.assertEqual(dates,sorted(dates,reverse=True));self.assertTrue(any('撤销' in r['kind'] or '修订' in r['kind'] for r in rows));self.assertTrue(any('?' in r['label'] for r in rows))
if __name__=='__main__':unittest.main()
