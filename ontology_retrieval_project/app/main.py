"""FastAPI app exposing hybrid search endpoints.
/index  -> POST to index documents (calls ingestion pipeline)
/search -> GET q, top_k (runs SPARQL to filter candidates + Qdrant vector search and returns hybrid ranking)
"""
from fastapi import FastAPI, Query
from pydantic import BaseModel
import os, requests, json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from SPARQLWrapper import SPARQLWrapper, JSON

app = FastAPI(title='Ontology-Driven Hybrid Retriever')

FUSEKI_QUERY = os.environ.get('FUSEKI_QUERY', 'http://localhost:3030/ds/query')
QDRANT_URL = os.environ.get('QDRANT_URL', 'http://localhost:6333')
QDRANT_COLLECTION = os.environ.get('QDRANT_COLLECTION', 'manuals')
model = SentenceTransformer('all-MiniLM-L6-v2')
qclient = QdrantClient(url=QDRANT_URL)

class IndexRequest(BaseModel):
    csv_path: str = '../sample_data/manuals.csv'

@app.post('/index')
def index(req: IndexRequest):
    # Simple wrapper that calls the ingestion script; this is intentionally light-weight.
    import subprocess, sys
    proc = subprocess.run([sys.executable, 'ingestion/ingest.py', '--csv', req.csv_path], capture_output=True, text=True)
    return {'stdout': proc.stdout, 'stderr': proc.stderr, 'returncode': proc.returncode}

@app.get('/search')
def search(q: str = Query(..., min_length=1), top_k: int = 5):
    # 1) Use SPARQL to find documents that mention tokens from the query (simple example)
    sparql = SPARQLWrapper(FUSEKI_QUERY)
    # Basic token splitting for demo; for production use proper NLP tokenization+mapping to ontology terms
    tokens = [t.strip() for t in q.split() if t.strip()]
    token_filters = ' '.join(f'FILTER(CONTAINS(LCASE(?text), "{t.lower()}"))' for t in tokens)
    sparql.setQuery(f'''
    PREFIX onto: <http://example.org/ontology#>
    PREFIX res: <http://example.org/resource/>
    SELECT ?doc ?title ?text WHERE {{
        ?doc onto:text ?text .
        ?doc onto:title ?title .
        {token_filters}
    }} LIMIT 50
    ''')
    sparql.setReturnFormat(JSON)
    try:
        res = sparql.query().convert()
        candidates = []
        for b in res['results']['bindings']:
            candidates.append({'id': b['doc']['value'].split('/')[-1], 'title': b['title']['value'], 'text': b['text']['value']})
    except Exception as e:
        candidates = []
    # 2) Dense retrieval via Qdrant
    qvec = model.encode([q])[0].tolist()
    try:
        search_res = qclient.search(collection_name=QDRANT_COLLECTION, query_vector=qvec, limit=top_k)
        qdrant_hits = [{'id': hit.id, 'score': hit.score, 'payload': hit.payload} for hit in search_res]
    except Exception as e:
        qdrant_hits = []
    # 3) Simple hybrid merge: prefer candidates that appear in both results, then qdrant hits, then SPARQL candidates
    merged = []
    ids_seen = set()
    for h in qdrant_hits:
        merged.append({'id': str(h['id']), 'source': 'qdrant', 'score': h.get('score'), 'payload': h.get('payload')})
        ids_seen.add(str(h['id']))
    for c in candidates:
        if c['id'] not in ids_seen:
            merged.append({'id': c['id'], 'source': 'sparql', 'title': c.get('title'), 'text': c.get('text')})
            ids_seen.add(c['id'])
    return {'query': q, 'results': merged}
