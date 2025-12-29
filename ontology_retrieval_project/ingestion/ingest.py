"""Ingestion pipeline:
- Read CSV manuals
- Extract simple entities (very small rule-based extractor in this example)
- Create RDF triples with rdflib and push to Fuseki via SPARQL Update
- Create embeddings with sentence-transformers and push to Qdrant
"""
import os
import csv
from rdflib import Graph, URIRef, Literal, Namespace, RDF
from SPARQLWrapper import SPARQLWrapper, POST
from sentence_transformers import SentenceTransformer
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

# Basic config defaults - override via args when calling scripts
FUSEKI_UPDATE_ENDPOINT = os.environ.get('FUSEKI_UPDATE', 'http://localhost:3030/ds/update')
FUSEKI_DATASET = os.environ.get('FUSEKI_DATASET', 'http://localhost:3030/ds')
QDRANT_URL = os.environ.get('QDRANT_URL', 'http://localhost:6333')
QDRANT_COLLECTION = os.environ.get('QDRANT_COLLECTION', 'manuals')

ONTO = Namespace('http://example.org/ontology#')
BASE = Namespace('http://example.org/resource/')

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_entities(text):
    # VERY simple rule-based extraction for demo purposes.
    entities = {
        'failure_modes': [],
        'procedures': []
    }
    tokens = text.replace(',', '').split()
    for t in tokens:
        if t.endswith('_wear') or t.endswith('_fault') or t in ('bearing_fault','seal_wear','belt_break','oil_leak','seat_erosion'):
            entities['failure_modes'].append(t)
    if 'Procedure:' in text:
        proc_part = text.split('Procedure:')[-1]
        procs = [p.strip() for p in proc_part.split(',') if p.strip()]
        entities['procedures'].extend(procs)
    return entities

def build_rdf_and_push(csv_path):
    g = Graph()
    g.bind('onto', ONTO)
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_uri = URIRef(BASE + 'doc/' + row['id'])
            g.add((doc_uri, RDF.type, ONTO.Document if hasattr(ONTO, 'Document') else RDF.Property))
            g.add((doc_uri, ONTO.title, Literal(row['title'])))
            g.add((doc_uri, ONTO.text, Literal(row['text'])))
            ents = extract_entities(row['text'])
            for fm in ents['failure_modes']:
                fm_uri = URIRef(BASE + 'failure/' + fm)
                g.add((fm_uri, RDF.type, ONTO.FailureMode))
                g.add((doc_uri, ONTO.canCause, fm_uri))
            for proc in ents['procedures']:
                proc_id = proc.replace(' ', '_')
                p_uri = URIRef(BASE + 'procedure/' + proc_id)
                g.add((p_uri, RDF.type, ONTO.Procedure))
                g.add((doc_uri, ONTO.hasProcedure, p_uri))
    # Serialize and push to Fuseki via SPARQL Update (INSERT DATA)
    ttl = g.serialize(format='turtle')
    sparql = SPARQLWrapper(FUSEKI_UPDATE_ENDPOINT)
    sparql.setMethod(POST)
    query = 'INSERT DATA { %s }' % ttl.decode('utf-8') if isinstance(ttl, bytes) else 'INSERT DATA { %s }' % ttl
    sparql.setQuery(query)
    sparql.query()
    print('Pushed RDF to Fuseki')

def build_embeddings_and_push(csv_path):
    df = []
    ids = []
    texts = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(int(row['id']))
            texts.append(row['text'])
    embeddings = model.encode(texts, convert_to_numpy=True)
    client = QdrantClient(url=QDRANT_URL)
    # create collection if not exists
    try:
        client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(size=embeddings.shape[1], distance=qmodels.Distance.COSINE)
        )
    except Exception:
        # might already exist; ignore
        pass
    points = []
    for i, e in enumerate(embeddings):
        points.append(qmodels.PointStruct(id=ids[i], vector=e.tolist(), payload={'title': f'doc_{ids[i]}'}))
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    print('Uploaded embeddings to Qdrant')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='../sample_data/manuals.csv')
    parser.add_argument('--fuseki', default=FUSEKI_UPDATE_ENDPOINT)
    parser.add_argument('--qdrant', default=QDRANT_URL)
    args = parser.parse_args()
    FUSEKI_UPDATE_ENDPOINT = args.fuseki
    QDRANT_URL = args.qdrant
    build_rdf_and_push(args.csv)
    build_embeddings_and_push(args.csv)
