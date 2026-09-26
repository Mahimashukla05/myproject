import pytest
import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['service'] == 'Parcel Routing System API'
    assert data['database'] in ['connected', 'unavailable']
    if data['database'] == 'connected':
        assert data['status'] == 'healthy'
    else:
        assert data['status'] == 'degraded'
