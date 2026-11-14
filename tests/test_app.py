from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_demo_app():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=45).run()
    assert not app.exception
    assert len(app.tabs)==4
    assert len(app.metric)==5
    assert len(app.get('download_button'))==3
    app.toggle[0].set_value(True).run()
    assert not app.exception
    app.toggle[1].set_value(True).run()
    assert not app.exception
    app.radio[0].set_value('CSV yükle').run()
    assert not app.exception
