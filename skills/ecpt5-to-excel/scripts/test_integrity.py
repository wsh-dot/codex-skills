"""Focused boundary tests; no private project fixtures are bundled."""
from pathlib import Path
import json, os, struct, subprocess, sys, unittest, uuid, zipfile
from unittest.mock import patch
from export_ecpt5 import preflight_database,extract_project,main
from ecpt5_model import build_model

class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ.get('ECPT5_TEST_ROOT',Path.cwd()/'ecpt5-integrity-tests')).resolve()/uuid.uuid4().hex[:10]
        cls.root.mkdir(parents=True)

    def test_database_prefix_and_corrupt_count(self):
        b=bytearray(512);b[:5]=b'db4o\x01';b[36]=8
        struct.pack_into('>i',b,37,10);struct.pack_into('>ii',b,80,20,12);struct.pack_into('>i',b,160,2)
        data,h=preflight_database(b'PREFIX'+b)
        self.assertEqual(data,bytes(b));self.assertEqual(h['prefixBytes'],6)
        struct.pack_into('>i',b,160,822095360)
        with self.assertRaisesRegex(ValueError,'DB_REPOSITORY_INVALID'):preflight_database(b)

    def test_unknown_header_is_rejected_before_library_open(self):
        b=bytearray(100);b[:5]=b'db4o\x02'
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED'):preflight_database(b)

    def test_zip_path_cannot_escape_work(self):
        zpath=self.root/'bad.ecpt5';work=self.root/'zip-work';work.mkdir()
        with zipfile.ZipFile(zpath,'w') as z:z.writestr('arr',b'xml');z.writestr('../escape.ecd',b'db4o')
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_DATABASE_ENTRY'):
            extract_project(zpath,work,'unused',self.root,1)
        self.assertFalse((self.root/'escape.ecd').exists())

    def test_zip_limit_precedes_crc_decompression(self):
        entry=zipfile.ZipInfo('safe.ecd');entry.file_size=2*1024**3
        class FakeZip:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def namelist(self):return ['arr','safe.ecd']
            def infolist(self):return [entry]
            def testzip(self):raise AssertionError('CRC called before declared size check')
        with patch('export_ecpt5.zipfile.ZipFile',return_value=FakeZip()):
            with self.assertRaisesRegex(ValueError,'EXCEEDS_1GIB'):extract_project(Path('fake'),self.root,'unused',self.root,1)

    def test_configuration_failure_does_not_masquerade_as_partial(self):
        with self.assertRaises(SystemExit) as c:main(['--output-dir',str(self.root)])
        self.assertEqual(c.exception.code,1)

    def test_unreadable_engine_preserves_summary_and_unknowns(self):
        work=self.root/'model';work.mkdir()
        (work/'arr.xml').write_text("""<?xml version='1.0' encoding='UTF-8'?><objects date='2026-10-25'><ProjInfoEntity id='project' orderCode='1' name='样例' bzcost='50'/><EditorCellEntity id='engine' orderCode='1.1' name='源工程' costFileId='budget' bzcost='50'/></objects>""",encoding='utf-8')
        d=build_model(work,Path('sample.ecpt5'),{'budget':'DB_TIMEOUT'},'sample')
        self.assertFalse(d['isComplete']);self.assertEqual(d['rows'][1][17],50)
        self.assertIsNone(d['rows'][1][9]);self.assertIsNone(d['checks'][0][8]);self.assertIsNone(d['checks'][0][9])
        self.assertEqual(d['readDatabases'],0);self.assertIn('未读取',d['rows'][1][19])

    def test_cbs_old_ids_do_not_reject_valid_budget(self):
        work=self.root/'cbs';work.mkdir()
        (work/'arr.xml').write_text("""<objects><ProjInfoEntity id='p' orderCode='1' name='CBS' bzcost='50'/><EditorCellEntity id='new-entity' orderCode='1.1' name='工程' costFileId='new-budget' bzcost='50'/></objects>""",encoding='utf-8')
        objs=[{'id':1,'type':'com.toone.CostFile','fields':{'id':'old-budget','editorCellEntityId':'old-entity','name':'工程','cost':50,'zmItemList':{'ref':2}}},{'id':2,'type':'com.toone.ZMItemList','fields':{'items':[{'ref':3}]}},{'id':3,'type':'com.toone.ZMItemEntity','fields':{'BSID':'1','name':'工程','mark':'工程','gcl':0,'unitPrice':0,'totalPrices':0,'zzj':50,'zcSpend':[],'rcjSpend':[]}}]
        (work/'new-budget.ecd.jsonl').write_text('\n'.join(json.dumps(o) for o in objs),encoding='utf-8')
        d=build_model(work,Path('cbs.ecpt5'),{},'cbs')
        self.assertTrue(d['isComplete']);self.assertEqual(d['readDatabases'],1);self.assertEqual(len(d['mapping']),1)
        self.assertTrue(d['rows'][1][18].startswith('new-budget:'))

    def test_shared_unreadable_database_does_not_produce_negative_counts(self):
        work=self.root/'shared';work.mkdir()
        (work/'arr.xml').write_text("""<objects><ProjInfoEntity id='p' orderCode='1' name='共享库' bzcost='100'/><EditorCellEntity id='a' orderCode='1.1' name='工程甲' costFileId='shared' bzcost='50'/><EditorCellEntity id='b' orderCode='1.2' name='工程乙' costFileId='shared' bzcost='50'/></objects>""",encoding='utf-8')
        d=build_model(work,Path('shared.ecpt5'),{'shared':'DB_TIMEOUT'},'shared')
        self.assertEqual((d['expectedDatabases'],d['readDatabases']),(1,0))
        self.assertEqual((d['expectedEngines'],d['readEngines']),(2,0))
        self.assertEqual(len(d['unreadable']),2)
        objs=[{'id':1,'type':'com.toone.CostFile','fields':{'id':'shared','editorCellEntityId':'a','name':'共享预算','cost':50,'zmItemList':{'ref':2}}},{'id':2,'type':'com.toone.ZMItemList','fields':{'items':[{'ref':3}]}},{'id':3,'type':'com.toone.ZMItemEntity','fields':{'BSID':'1','name':'共享预算','mark':'工程','gcl':0,'unitPrice':0,'totalPrices':0,'zzj':50,'zcSpend':[],'rcjSpend':[]}}]
        (work/'shared.ecd.jsonl').write_text('\n'.join(json.dumps(o) for o in objs),encoding='utf-8')
        complete=build_model(work,Path('shared.ecpt5'),{},'shared')
        self.assertTrue(complete['isComplete'])
        self.assertEqual((complete['expectedDatabases'],complete['readDatabases']),(1,1))
        self.assertEqual((complete['expectedEngines'],complete['readEngines']),(2,2))

if __name__=='__main__':unittest.main()
