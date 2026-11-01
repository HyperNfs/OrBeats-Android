# SPDX-License-Identifier: GPL-3.0-only
"""In-app generated-data self-check. Never opens songs or a console connection."""
import json
import os
from pathlib import Path
import runpy
import tempfile


def check(cache):
    with tempfile.TemporaryDirectory(prefix='orbeats-engine-', dir=cache) as work:
        report = Path(work)/'report.json'
        previous = os.environ.get('ORBEATS_WRITER_REPORT')
        os.environ['ORBEATS_WRITER_REPORT'] = str(report)
        try:
            runpy.run_module('writer_probe', run_name='__orbeats_probe__')
            result = json.loads(report.read_text())
            if len(result['generated_unityfs_roundtrips']) != 4:
                raise RuntimeError('UnityFS self-check incomplete')
            return json.dumps(result)
        finally:
            if previous is None:
                os.environ.pop('ORBEATS_WRITER_REPORT', None)
            else:
                os.environ['ORBEATS_WRITER_REPORT'] = previous
