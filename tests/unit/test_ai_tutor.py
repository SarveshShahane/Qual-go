import pytest
from httpx import AsyncClient, ASGITransport

from app.app import app
from app.services.ai.rag_service import rag_service
from app.services.ai.recommendation_service import recommendation_service


@pytest.fixture
def bell_circuit():
    return {
        "name": "Bell State (|Φ⁺⟩)",
        "qubits": 2,
        "classicalBits": 2,
        "moments": [
            {
                "operations": [
                    {"gate": "H", "targets": [0]}
                ]
            },
            {
                "operations": [
                    {"gate": "CX", "targets": [1], "controls": [0]}
                ]
            },
        ],
    }


def test_rag_knowledge_base():
    """Verify curriculum chunks are indexed and searchable."""
    results = rag_service.search("superposition", top_k=3)
    assert len(results) > 0
    chunk, score, source = results[0]
    assert chunk.module_id != ""
    assert "superposition" in chunk.content.lower() or "qubit" in chunk.content.lower() or "state" in chunk.content.lower()
    assert source.module_id != ""


def test_recommendation_service():
    """Verify recommendation logic computes mastery and next steps."""
    recs = recommendation_service.generate_recommendations()
    assert len(recs) > 0
    assert recs[0].target_module != ""


@pytest.mark.asyncio
async def test_ai_chat_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "prompt": "What is quantum superposition?",
            "context": {
                "user_level": "beginner",
                "tutoring_mode": "explain",
            },
        }
        res = await client.post("/api/v1/ai/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["type"] in ["explanation", "socratic", "code"]
        assert "superposition" in data["message"].lower() or len(data["message"]) > 20
        assert "provider" in data


@pytest.mark.asyncio
async def test_ai_explain_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "concept": "Hadamard Gate",
            "context": {
                "user_level": "intermediate",
            },
        }
        res = await client.post("/api/v1/ai/explain", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "explanation"
        assert len(data["message"]) > 0


@pytest.mark.asyncio
async def test_ai_generate_code_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "prompt": "Create a Bell state using Qiskit",
            "target_framework": "qiskit",
        }
        res = await client.post("/api/v1/ai/generate-code", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "code"
        assert data["code"] is not None
        assert "QuantumCircuit" in data["code"]


@pytest.mark.asyncio
async def test_ai_generate_circuit_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "prompt": "Create a Bell state",
        }
        res = await client.post("/api/v1/ai/generate-circuit", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["circuit"] is not None
        assert data["circuit"]["qubits"] >= 2
        assert len(data["circuit"]["moments"]) >= 2


@pytest.mark.asyncio
async def test_ai_debug_endpoint(bell_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_circuit,
            "error_message": "Control and target qubit are identical: q0",
        }
        res = await client.post("/api/v1/ai/debug", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "debug"
        assert data["diagnostics"] is not None
        assert len(data["diagnostics"]) > 0
        diag = data["diagnostics"][0]
        assert "cause" in diag
        assert "suggested_fix" in diag


@pytest.mark.asyncio
async def test_ai_hint_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test hint level 1
        res1 = await client.post("/api/v1/ai/hint", json={"hint_level": 1, "challenge_id": "bell_state"})
        assert res1.status_code == 200
        d1 = res1.json()
        assert d1["type"] == "hint"
        assert d1["hints"] is not None
        assert d1["hints"][0]["level"] == 1

        # Test hint level 4 (solution)
        res4 = await client.post("/api/v1/ai/hint", json={"hint_level": 4, "challenge_id": "bell_state"})
        assert res4.status_code == 200
        d4 = res4.json()
        assert d4["hints"][0]["level"] == 4


@pytest.mark.asyncio
async def test_ai_recommendations_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "profile": {
                "completed_topics": ["vectors", "dirac_notation"],
                "assessment_scores": {"vectors": 0.95, "dirac_notation": 0.8},
            }
        }
        res = await client.post("/api/v1/ai/recommendations", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "recommendation"
        assert data["recommendations"] is not None
        assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_ai_analyze_circuit_endpoint(bell_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/ai/analyze-circuit", json=bell_circuit)
        assert res.status_code == 200
        data = res.json()
        assert "Quantum State Evolution Analysis" in data["message"]
        assert "Hadamard" in data["message"] or "H" in data["message"]
