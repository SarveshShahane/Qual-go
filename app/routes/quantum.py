import asyncio
import time
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.schemas.quantum import (
    BackendInfo,
    CanonicalCircuit,
    SimulationRequest,
    SimulationResponse,
    TranspileRequest,
    TranspileResponse,
)
from app.services.quantum.backend_registry import backend_registry

router = APIRouter(prefix="/quantum", tags=["Quantum Multi-Backend Simulation"])


@router.get(
    "/backends",
    response_model=List[BackendInfo],
    summary="List available quantum execution backends",
)
async def get_backends():
    """
    Returns metadata, status, framework versions, and capabilities for all supported quantum backends
    (Qiskit Aer, Google Cirq, Xanadu PennyLane, qBraid, and In-Browser client).
    """
    return backend_registry.list_backends()


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Execute or simulate a quantum circuit on a specified backend",
)
async def simulate_circuit(request: SimulationRequest):
    """
    Executes a Canonical Circuit IR on the chosen backend (Qiskit Aer, Cirq, PennyLane, or qBraid),
    returning exact statevector, Bloch sphere vectors, measurement histogram counts, and probabilities.
    """
    try:
        return await backend_registry.execute_circuit(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quantum simulation failed on backend '{request.backend}': {str(e)}",
        )


@router.post(
    "/transpile",
    response_model=TranspileResponse,
    summary="Transpile a circuit into framework-specific code",
)
async def transpile_circuit(request: TranspileRequest):
    """
    Transpiles the canonical circuit into executable code for Qiskit, Cirq, PennyLane, or qBraid.
    """
    try:
        return backend_registry.transpile_circuit(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Circuit transpilation failed: {str(e)}",
        )


class CompareRequest(SimulationRequest):
    backends: List[str] = ["qiskit_aer", "cirq", "pennylane"]


class CompareResponse(SimulationResponse):
    pass


@router.post(
    "/compare",
    summary="Execute circuit across multiple backends concurrently for verification",
)
async def compare_backends(request: CompareRequest):
    """
    Executes a circuit concurrently across multiple backends (e.g. Qiskit Aer, Cirq, PennyLane)
    to compare fidelity, statevector equivalence, and execution latency.
    """
    results: Dict[str, Any] = {}

    async def _run_backend(b_id: str):
        try:
            req = SimulationRequest(
                circuit=request.circuit,
                backend=b_id, # type: ignore
                shots=request.shots,
                options=request.options,
            )
            res = await backend_registry.execute_circuit(req)
            return b_id, res.model_dump()
        except Exception as e:
            return b_id, {"error": str(e), "success": False}

    tasks = [_run_backend(b_id) for b_id in request.backends]
    completed = await asyncio.gather(*tasks)

    for b_id, res in completed:
        results[b_id] = res

    return {
        "success": True,
        "circuit_name": request.circuit.name,
        "qubits": request.circuit.qubits,
        "shots": request.shots,
        "results": results,
    }
