import sys, os
# add backend directory to path regardless of cwd
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(backend_dir)

from starlette.testclient import TestClient
import app

client = TestClient(app.app)

path = r'c:\Users\Cc\Desktop\New folder (2)\إحصائية تقديرات المواد حديثة.xlsx'


# directly replicate logic to see serialized values
import io, pandas as pd
from quality import compute_kpis
from ml_models import predict_quality_degradation, course_risk_probabilities
from academic_analytics import compute_academic_analytics
from course_plans import generate_course_plans
from statistics_program import compute_program_statistics
from statistics_cross import compute_cross_module_and_executive
from alerts import generate_alerts

with open(path, 'rb') as f:
    contents = f.read()

# try reading excel with adaptive helper (same logic used by the endpoint)
from excel_reader import read_excel_adaptive
try:
    dfs = read_excel_adaptive(io.BytesIO(contents))
except Exception as e:
    print('adaptive read error', e)
    raise

schema_info = {sheet: list(df.columns) for sheet, df in dfs.items()}

kpi_results = {sheet: compute_kpis(df) for sheet, df in dfs.items()}
academic = {sheet: compute_academic_analytics(df, {}) for sheet, df in dfs.items()}

metadata = {
    'filename': 'test.xlsx',
    'timestamp': pd.Timestamp.now().isoformat(),
    'sheets': list(dfs.keys()),
    'schema': schema_info,
    'kpis': kpi_results,
}

predictions = predict_quality_degradation(kpi_results)
course_risk = course_risk_probabilities(academic)
course_plans = generate_course_plans(academic, course_risk, predictions)
program_stats = compute_program_statistics(academic, kpi_results)
cross_stats = compute_cross_module_and_executive(kpi_results, predictions, None, program_stats)
alerts_list = generate_alerts(kpi_results, predictions, {
    'duplicate_rate': 5,
    'anomaly_density': 0.1,
    'quality_score': 0.8,
})

print('metadata type', type(metadata))
print('predictions type', type(predictions))
print('course_risk type', type(course_risk))
print('course_plans type', type(course_plans))
print('program_stats type', type(program_stats))
print('cross_stats type', type(cross_stats))
print('alerts_list type', type(alerts_list))

# recursively inspect for numpy types
import numpy as np

def recurse(obj, path="root"):
    if isinstance(obj, dict):
        for k,v in obj.items():
            recurse(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for idx,v in enumerate(obj):
            recurse(v, f"{path}[{idx}]")
    else:
        if isinstance(obj, (np.generic,)):
            print(f"{path} is numpy type {type(obj)} value {obj}")
        elif isinstance(obj, bool) and not isinstance(obj, bool):
            print(f"{path} potential bool issue {type(obj)} {obj}")

# check each component
recurse(predictions, 'predictions')
recurse(course_risk, 'course_risk')
recurse(course_plans, 'course_plans')
recurse(program_stats, 'program_stats')
recurse(cross_stats, 'cross_stats')
recurse(alerts_list, 'alerts_list')
# include kpis and schema
recurse(kpi_results, 'kpi_results')
recurse(schema_info, 'schema_info')

# show sample from predictions maybe causing numpy.bool
import numpy as np

def inspect(obj, name):
    if isinstance(obj, dict):
        for k,v in obj.items():
            print(name, k, type(v), v if not isinstance(v, (np.ndarray,)) else 'array')
    else:
        print(name, type(obj), obj)

inspect(predictions, 'predictions')
inspect(course_risk, 'course_risk')
inspect(course_plans, 'course_plans')
inspect(program_stats, 'program_stats')
inspect(cross_stats, 'cross_stats')
inspect(alerts_list, 'alerts_list')

# try encoding each component separately to isolate the problematic value
from fastapi.encoders import jsonable_encoder
components = {
    'metadata': metadata,
    'predictions': predictions,
    'alerts': alerts_list,
    'academic_analytics': academic,
    'course_risk': course_risk,
    'course_plans': course_plans,
    'program_statistics': program_stats,
    'cross_module': cross_stats,
}
for name, val in components.items():
    try:
        jsonable_encoder(val)
        print(f'{name} encodable')
    except Exception as ee:
        print(f'{name} failed encoding: {ee}')
        recurse(val, name)

# now try the full payload
try:
    jsonable_encoder(components)
    print('full payload encodable')
except Exception as e:
    print('full payload encoding failed', e)


# also send to endpoint to see response
with open(path, 'rb') as f2:
    response = client.post(
        '/upload-excel',
        files={'file': ('test.xlsx', f2, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    )
print('status', response.status_code)
print(response.text)
