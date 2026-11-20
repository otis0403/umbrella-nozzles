import json
import tempfile
from pathlib import Path
import ansys.fluent.core as pf

ROOT=Path(__file__).resolve().parent
def connect(transcript=True,cleanup=False):
    kw=json.loads((Path(tempfile.gettempdir())/'umbrella_fluent_connection_20261105.json').read_text())
    return pf.connect_to_fluent(**kw,cleanup_on_exit=cleanup,start_watchdog=False,start_transcript=transcript)
