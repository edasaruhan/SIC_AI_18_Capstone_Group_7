"""Streamlit executes the shared model when the scenario is changed."""
from streamlit.testing.v1 import AppTest
from analysis.config import ROOT
from deployment.inference import ResearchModel

def test_dashboard_loads_real_results_and_recalculates_scenarios():
    at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
    assert not at.exception
    assert len(at.dataframe) >= 1
    assert 'GDT analizi' in [v.label for v in at.metric]
    before = next(v.value for v in at.metric if v.label == 'Tahmin edilen sonraki GDT toplamı')
    at.selectbox[1].select('example_b').run()
    assert not at.exception
    after = next(v.value for v in at.metric if v.label == 'Tahmin edilen sonraki GDT toplamı')
    assert before != after
    assert float(after) == ResearchModel().predict('example_b')['predicted_gdt_total']
    at.selectbox[0].select('RQ2 · sonraki rutin müdahalesi').run()
    assert not at.exception
