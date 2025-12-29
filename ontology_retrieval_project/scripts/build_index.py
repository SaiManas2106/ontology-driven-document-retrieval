"""Helper script to build RDF and Qdrant index using ingestion/ingest.py
Usage: python scripts/build_index.py --fuseki http://localhost:3030/ds/update --qdrant http://localhost:6333
"""
import argparse, subprocess, sys
parser = argparse.ArgumentParser()
parser.add_argument('--fuseki', default='http://localhost:3030/ds/update')
parser.add_argument('--qdrant', default='http://localhost:6333')
parser.add_argument('--csv', default='../sample_data/manuals.csv')
args = parser.parse_args()
ret = subprocess.run([sys.executable, 'ingestion/ingest.py', '--csv', args.csv, '--fuseki', args.fuseki, '--qdrant', args.qdrant])
if ret.returncode != 0:
    raise SystemExit('Indexing failed')
print('Indexing completed')
