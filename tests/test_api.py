from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_anonymize_endpoint_txt():
    files = {"file": ("teste.txt", b"Meu CPF 123.456.789-00", "text/plain")}
    data = {"engine": "regex"}
    response = client.post("/api/v1/anonymize/", files=files, data=data)
    
    assert response.status_code == 200
    json_resp = response.json()
    assert "[CPF_ANONIMIZADO]" in json_resp["anonymized_text"]
    assert len(json_resp["entities_found"]) == 1