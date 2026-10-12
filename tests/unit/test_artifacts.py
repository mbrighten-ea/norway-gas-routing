"""Failed publication cannot destroy saved assessments or overwrite experiments."""
import json
import pytest
from norway_gas_routing.artifacts import new_experiment, publish_assessment
from norway_gas_routing.evaluation import reconstruction_evaluation
from norway_gas_routing.evaluation import EvaluationError
import pandas as pd

def test_experiment_sequence_includes_retained_milestones(tmp_path):
    (tmp_path/'archive/20261009-02_capacity-review').mkdir(parents=True)
    first=new_experiment(tmp_path,'source-accounting','20261009')
    second=new_experiment(tmp_path,'source-accounting','20261009')
    assert first.name=='20261009-03_source-accounting'
    assert second.name=='20261009-04_source-accounting'
    assert first.is_dir()

def test_failed_candidate_leaves_previous_assessment_untouched(tmp_path):
    current=tmp_path/'outputs/reconstruction'
    current.mkdir(parents=True)
    (current/'results.csv').write_text('retained original')
    candidate=new_experiment(tmp_path,'baseline-routing','20261009')
    (candidate/'provenance').mkdir()
    (candidate/'provenance/run_manifest.json').write_text(json.dumps({'status':'BLOCKED_NO_SOLVER'}))
    with pytest.raises(ValueError,match='failed'):
        publish_assessment(tmp_path,candidate,'reconstruction')
    assert (current/'results.csv').read_text()=='retained original'
    assert candidate.exists()

@pytest.mark.parametrize('results', ['month,value\n2024-01,1\n', 'month,value\n2024-02,1\n',
                                     'value\n1\n', 'month,value\n,1\n'])
def test_successful_publication_retains_previous_result_in_scratch(tmp_path, results):
    current=tmp_path/'outputs/reconstruction'
    current.mkdir(parents=True)
    (current/'results.csv').write_text('original')
    candidate=new_experiment(tmp_path,'baseline-routing','20261009')
    (candidate/'provenance').mkdir()
    settings = {'baseline_start': '2023-01', 'baseline_end': '2023-12'}
    inputs = {'months': pd.period_range('2024-01', periods=1, freq='M'),
              'training_observations': pd.DataFrame(index=pd.period_range('2023-01', periods=12, freq='M')),
              'preferences': {'UK': 1.}, 'provenance': []}
    manifest = {'status': 'OPTIMAL', 'run_id': candidate.name,
                'evaluation': reconstruction_evaluation(tmp_path, inputs, settings, candidate.name)}
    (candidate/'provenance/run_manifest.json').write_text(json.dumps(manifest))
    (candidate/'results.csv').write_text(results)
    (candidate/'report.html').write_text('new report')
    if results != 'month,value\n2024-01,1\n':
        with pytest.raises(EvaluationError):
            publish_assessment(tmp_path,candidate,'reconstruction')
        assert (current/'results.csv').read_text() == 'original'
        assert candidate.exists()
        return
    publish_assessment(tmp_path,candidate,'reconstruction')
    assert (current/'results.csv').read_text()=='month,value\n2024-01,1\n'
    assert any(path.read_text()=='original' for path in (tmp_path/'.scratch/runs').rglob('results.csv'))
