# Test share page
import sys
sys.path.insert(0, r'C:\Users\Administrator\Projects\digital_human_ai')

from web.app import app

with app.test_client() as client:
    # Test share page
    resp = client.get('/share')
    print(f"GET /share: {resp.status_code}")
    
    # Check if it contains our content
    content = resp.get_data(as_text=True)
    print(f"Has share.html content: {'数字人AI' in content and '问卷' in content}")
    
    # Test API endpoints
    resp = client.get('/api/questionnaires')
    print(f"GET /api/questionnaires: {resp.status_code}")
    
    data = resp.get_json()
    print(f"Questionnaires count: {len(data.get('questionnaires', []))}")
