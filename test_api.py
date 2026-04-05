# Test script
import sys
sys.path.insert(0, r'C:\Users\Administrator\Projects\digital_human_ai')

try:
    from web.app import app
    print("Flask app import OK")
    
    # Test request
    with app.test_client() as client:
        # Test questionnaires endpoint
        resp = client.get('/api/questionnaires')
        print(f"GET /api/questionnaires: {resp.status_code}")
        print(resp.get_json())
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
