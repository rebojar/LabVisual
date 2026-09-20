"""Contratos matemáticos e de compatibilidade, sem carregar pesos."""
from pathlib import Path
import copy, importlib.util, json, sys, tempfile, unittest
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import analysis
import neighbors

class AnalysisTests(unittest.TestCase):
    def test_pooling_uses_each_coordinate_across_tokens(self):
        tokens=np.array([[1.,-5.,9.],[3.,-2.,1.],[8.,-8.,5.]],dtype=np.float32)
        np.testing.assert_allclose(analysis.aggregate(tokens,'mean'),[4.,-5.,5.])
        np.testing.assert_array_equal(analysis.aggregate(tokens,'max'),[8.,-2.,9.])
        np.testing.assert_array_equal(analysis.aggregate(tokens,'median'),[3.,-5.,5.])
        np.testing.assert_array_equal(analysis.aggregate(np.array([[1.,7.],[3.,1.]]),'median'),[2.,4.])

    def test_normalization_definitions_and_sign(self):
        raw=np.array([-3.,4.])
        for method,expected,divisor in [('l1',[-3/7,4/7],7),('l2',[-.6,.8],5),('linf',[-.75,1.],4),('none',[-3,4],1)]:
            with self.subTest(method=method):
                v,d=analysis.normalize(raw,method)
                np.testing.assert_allclose(v,expected);self.assertEqual(d,divisor)
        np.testing.assert_array_equal(raw,[-3,4])

    def test_cosine_invariance_and_different_euclidean_rank(self):
        a=np.array([[1.,0.],[100.,1.],[0.,1.],[-1.,0.]])
        base=analysis.ranking(a,0,'cosine')
        for method in ('l1','l2','linf'):
            b=np.stack([analysis.normalize(v,method)[0] for v in a])
            got=analysis.ranking(b,0,'cosine')
            self.assertEqual([v['index'] for v in got['neighbors']],[v['index'] for v in base['neighbors']])
            np.testing.assert_allclose([v['score'] for v in got['neighbors']],[v['score'] for v in base['neighbors']],atol=1e-15)
        self.assertEqual(analysis.ranking(a,0,'euclidean')['neighbors'][0]['index'],2)
        self.assertEqual(analysis.ranking(np.stack([analysis.normalize(v)[0] for v in a]),0,'euclidean')['neighbors'][0]['index'],1)

    def test_dot_not_clipped_self_excluded_and_ties_stable(self):
        r=analysis.ranking(np.array([[2.,0.],[5.,0.],[5.,0.],[-8.,0.]]),0,'dot')
        self.assertEqual([v['index'] for v in r['neighbors']],[1,2,3])
        self.assertEqual(r['neighbors'][0]['score'],10)
        self.assertEqual(r['neighbors'][2]['score'],-16)
        self.assertTrue(r['higher_is_closer'])
        self.assertFalse(analysis.ranking(np.array([[2.,0.],[5.,0.]]),0,'euclidean')['higher_is_closer'])

    def test_null_nonfinite_and_invalid_recipes(self):
        for method in ('l1','l2','linf'):
            with self.assertRaises(ValueError):analysis.normalize(np.zeros(3),method)
        np.testing.assert_array_equal(analysis.normalize(np.zeros(3),'none')[0],np.zeros(3))
        with self.assertRaises(ValueError):analysis.ranking(np.zeros((2,3)),0,'cosine')
        self.assertEqual(analysis.ranking(np.zeros((2,3)),0,'euclidean')['neighbors'][0]['score'],0)
        for invalid in ({'normalization':'inventada'},{'pooling':'first'},{'metric':'invalid'},{'version':True},{'other':1},[]):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):analysis.recipe(invalid)
        with self.assertRaises(ValueError):analysis.aggregate(np.array([[np.nan,1.]]))

    def test_reanalysis_preserves_tokens_and_legacy_fields(self):
        import engine
        tokens=np.arange(30,dtype=np.float32).reshape(5,6)-11
        legacy={'antes':tokens.copy(),'depois':tokens.copy()+1,'info':{},'vetor_medio':np.ones(6),'vetor_unitario':np.ones(6)}
        before=copy.deepcopy(legacy)
        out=engine.reanalisar(legacy,{'pooling':'max','normalization':'linf','metric':'euclidean'})
        for name in ('antes','depois','vetor_medio','vetor_unitario'):
            np.testing.assert_array_equal(legacy[name],before[name]);np.testing.assert_array_equal(out[name],before[name])
        self.assertNotIn('analysis',legacy)
        self.assertEqual(out['analysis']['recipe']['pooling'],'max')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'values.npz';engine.salvar_resultado(out,p)
            with np.load(p,allow_pickle=False) as saved:
                np.testing.assert_array_equal(saved['antes_merger'],tokens)
                self.assertEqual(json.loads(saved['receita_json'].item())['normalization'],'linf')

    def test_energy_share_not_assumed_unit_length(self):
        self.assertAlmostEqual(float(analysis.squared_share(np.array([3.,4.]),1)),.64)
        self.assertEqual(float(analysis.squared_share(np.zeros(2),1)),0.)

    def test_batch_metadata_mismatch_rejected_and_legacy_explicit(self):
        oldroot=neighbors.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td);neighbors.ROOT=root;neighbors.CACHE.clear()
                folder=root/'batches'/'example';folder.mkdir(parents=True)
                r=analysis.recipe({'pooling':'max','normalization':'l1','metric':'euclidean'})
                enc={'adapter':'test-fixture'}
                meta={'folder_source':str(root),'recipe':r,'encoder':enc,'representation_schema':2,
                      'options':{'limit':256,'variant':'original','background':'#ffffff'},
                      'records':[{'state':'ok','analysis':{'recipe':r,'dimensions':{'before':2,'after':3}}}]}
                record=folder/'registro.json';record.write_text(json.dumps(meta))
                np.savez(folder/'embeddings.npz',arquivos=['example.png'],embedding_antes_merger=[[1.,2.]],embedding_depois_merger=[[1.,2.,3.]],receita_json=analysis.recipe_json(r),encoder_json=json.dumps(enc))
                d=neighbors.dataset('batch_example');self.assertEqual(d['recipe'],r)
                meta['recipe']=analysis.recipe();record.write_text(json.dumps(meta));neighbors.CACHE.clear()
                with self.assertRaises(ValueError):neighbors.dataset('batch_example')
                record.write_text(json.dumps({'folder_source':str(root),'options':meta['options']}))
                np.savez(folder/'embeddings.npz',arquivos=['example.png'],embedding_antes_merger=np.ones((1,1152)),embedding_depois_merger=np.ones((1,4096)))
                neighbors.CACHE.clear();d=neighbors.dataset('batch_example')
                self.assertTrue(d['legacy']);self.assertEqual(d['recipe'],analysis.DEFAULT)
                self.assertEqual(neighbors.compare('batch_example',0)['before']['neighbors'],[])
        finally:neighbors.ROOT=oldroot;neighbors.CACHE.clear()

    def test_sync_preserves_data_and_blocks_local_edits(self):
        spec=importlib.util.spec_from_file_location('sync_code',ROOT/'tools/sync_code.py')
        sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'runtime'
            sync.synchronize(target,True)
            (target/'sessions').mkdir();(target/'sessions'/'private.txt').write_text('local data')
            (target/'config-local.json').write_text('{}')
            self.assertEqual(sync.synchronize(target)['differences'],[])
            (target/'analysis.py').write_text('# local edit')
            self.assertIn('analysis.py',sync.synchronize(target)['conflicts'])
            with self.assertRaises(ValueError):sync.synchronize(target,True)
            self.assertEqual((target/'sessions'/'private.txt').read_text(),'local data')
            self.assertEqual((target/'config-local.json').read_text(),'{}')

if __name__=='__main__':unittest.main(verbosity=2)
