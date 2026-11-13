import pytest
from httpx import AsyncClient, ASGITransport

from app.app import app
from app.schemas.quantum import CanonicalCircuit, QuantumMoment, QuantumOperation


@pytest.fixture
def bell_state_circuit():
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
            {
                "operations": [
                    {"gate": "Measure", "targets": [0], "metadata": {"classicalTarget": 0}},
                    {"gate": "Measure", "targets": [1], "metadata": {"classicalTarget": 1}},
                ]
            }
        ]
    }


@pytest.mark.asyncio
async def test_get_quantum_backends():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/quantum/backends")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        backend_ids = [b["id"] for b in data]
        assert "qiskit_aer" in backend_ids
        assert "cirq" in backend_ids
        assert "pennylane" in backend_ids
        assert "qbraid" in backend_ids
        assert "client" in backend_ids


@pytest.mark.asyncio
async def test_simulate_qiskit_aer(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_state_circuit,
            "backend": "qiskit_aer",
            "shots": 500,
        }
        response = await client.post("/api/v1/quantum/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "qiskit_aer"
        assert data["shots"] == 500
        assert data["qubits"] == 2
        # Check probabilities: Bell state should have approx 0.5 for |00> and 0.5 for |11>
        assert "00" in data["probabilities"]
        assert "11" in data["probabilities"]
        assert abs(data["probabilities"]["00"] - 0.5) < 0.05
        assert abs(data["probabilities"]["11"] - 0.5) < 0.05
        # Total counts should equal shots
        counts = data["counts"]
        total_counts = sum(counts.values())
        assert total_counts == 500
        # Check Bloch vectors
        assert "blochVectors" in data
        assert len(data["blochVectors"]) == 2


@pytest.mark.asyncio
async def test_simulate_cirq(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_state_circuit,
            "backend": "cirq",
            "shots": 500,
        }
        response = await client.post("/api/v1/quantum/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "cirq"
        assert data["shots"] == 500
        assert abs(data["probabilities"]["00"] - 0.5) < 0.05
        assert abs(data["probabilities"]["11"] - 0.5) < 0.05
        assert sum(data["counts"].values()) == 500


@pytest.mark.asyncio
async def test_simulate_pennylane(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_state_circuit,
            "backend": "pennylane",
            "shots": 200,
        }
        response = await client.post("/api/v1/quantum/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "pennylane"
        assert data["shots"] == 200
        assert abs(data["probabilities"]["00"] - 0.5) < 0.05
        assert abs(data["probabilities"]["11"] - 0.5) < 0.05
        assert sum(data["counts"].values()) == 200


@pytest.mark.asyncio
async def test_simulate_qbraid(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_state_circuit,
            "backend": "qbraid",
            "shots": 100,
        }
        response = await client.post("/api/v1/quantum/simulate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "qbraid"
        assert sum(data["counts"].values()) == 100


@pytest.mark.asyncio
async def test_transpile_circuit(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Transpile to Cirq
        res_cirq = await client.post(
            "/api/v1/quantum/transpile",
            json={"circuit": bell_state_circuit, "target_framework": "cirq"},
        )
        assert res_cirq.status_code == 200
        assert "import cirq" in res_cirq.json()["code"]

        # Transpile to PennyLane
        res_qml = await client.post(
            "/api/v1/quantum/transpile",
            json={"circuit": bell_state_circuit, "target_framework": "pennylane"},
        )
        assert res_qml.status_code == 200
        assert "import pennylane as qml" in res_qml.json()["code"]


@pytest.mark.asyncio
async def test_compare_backends(bell_state_circuit):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "circuit": bell_state_circuit,
            "backends": ["qiskit_aer", "cirq", "pennylane"],
            "shots": 100,
        }
        response = await client.post("/api/v1/quantum/compare", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "qiskit_aer" in data["results"]
        assert "cirq" in data["results"]
        assert "pennylane" in data["results"]
