import requests
import sys
q = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'replace seal'
res = requests.get('http://localhost:8000/search', params={'q': q, 'top_k': 5})
print(res.json())
