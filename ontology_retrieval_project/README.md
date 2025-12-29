# Ontology-Driven Document Retrieval with Semantic Reasoning

**Project duration:** Mar 2025 – Jun 2025

**Stack:** Python, OWL, RDF, SPARQL, Sentence-Transformers, Qdrant, Apache Jena (Fuseki), FastAPI, Docker Compose

## Overview
This repository demonstrates a hybrid retrieval system that combines:
- an OWL ontology (OWL/RDF) to model domain concepts and relationships,
- a triple store (Apache Jena Fuseki) for structured retrieval via SPARQL,
- dense vector search in Qdrant (embeddings from Sentence-Transformers),
- a pipeline to convert documents into RDF triples + dense vectors,
- a FastAPI service exposing indexing and query endpoints that perform hybrid ranking.

The project includes:
- `ontology/ontology.owl` : example OWL ontology
- `ingestion/` : scripts to parse documents, create RDF triples, and push embeddings to Qdrant
- `app/` : FastAPI application for indexing and searching
- `docker-compose.yml` : Compose file to run Fuseki and Qdrant locally for testing
- `sample_data/manuals.csv` : small example dataset
- `scripts/` : helper scripts to build index and demo searches

## Quick setup (development)

1. Install Python 3.10+ and Docker + Docker Compose.
2. (Optional) Create virtualenv:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Start services (Fuseki + Qdrant):
   ```
   docker-compose up -d
   ```
   - Fuseki will be available at `http://localhost:3030`
   - Qdrant HTTP: `http://localhost:6333`
4. Create dataset + index (example):
   ```
   python scripts/build_index.py --fuseki http://localhost:3030/ds --qdrant http://localhost:6333
   ```
5. Run API:
   ```
   uvicorn app.main:app --reload --port 8000
   ```
6. Query:
   - Hybrid search: `GET http://localhost:8000/search?q=how+to+replace+valve&top_k=5`

## Notes
- The code uses `rdflib` and `SPARQLWrapper` to interact with RDF and Fuseki.
- Embeddings use `sentence-transformers`. The example uses `all-MiniLM-L6-v2` but you can change it in `config.py`.
- Qdrant client is used to store vectors and metadata. The code falls back to local in-memory storage if Qdrant isn't reachable (see docs).
- This repo is a starting point: adapt entity extraction and ontology modeling for your domain.

## Project structure
```
ontology_retrieval_project/
├─ app/
│  └─ main.py
├─ ingestion/
│  └─ ingest.py
├─ ontology/
│  └─ ontology.owl
├─ scripts/
│  ├─ build_index.py
│  └─ search_demo.py
├─ sample_data/
│  └─ manuals.csv
├─ requirements.txt
├─ docker-compose.yml
└─ README.md
```

## Contact
If you want more features (evaluation harness, unit tests, dataset loader integrations, or GitHub CI), tell me what to add and I'll update the repo.
