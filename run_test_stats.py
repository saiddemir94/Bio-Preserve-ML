import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from pipeline import process_sequences_dataframe

df = pd.read_csv('data/database_peptides.csv')
print('Test dizisi sayisi:', len(df))

result = process_sequences_dataframe(df)

bio_fail = result[~result['passed_biological_rules']]
bio_pass = result[result['passed_biological_rules']]
ml_rejected = bio_pass[bio_pass['ml_prediction'] == 0]
approved = result[result['final_status'] == 'Approved']
ml_scored = result[result['ml_probability'] > 0]

print(f'Biyolojik filtre gecemeyen : {len(bio_fail)} ({len(bio_fail)/len(result)*100:.1f}%)')
print(f'Biyolojik filtre gecen     : {len(bio_pass)} ({len(bio_pass)/len(result)*100:.1f}%)')
print(f'ML tarafindan elenen       : {len(ml_rejected)} ({len(ml_rejected)/len(result)*100:.1f}%)')
print(f'Onaylanan aday             : {len(approved)} ({len(approved)/len(result)*100:.1f}%)')
print(f'Ort. ML skoru              : {ml_scored["ml_probability"].mean():.4f}')
