from typing import Dict, List, Optional
from fastapi import HTTPException

from app.schemas.quantum import (
    BackendInfo,
    BackendStatus,
    BackendType,
    CanonicalCircuit,
    SimulationRequest,
    SimulationResponse,
    TranspileRequest,
    TranspileResponse,
)
from app.services.quantum.base_backend import QuantumBackendRunner
from app.services.quantum.cirq_runner import CirqRunner
from app.services.quantum.pennylane_runner import PennyLaneRunner
from app.services.quantum.qbraid_runner import QBraidRunner
from app.services.quantum.qiskit_runner import QiskitAerRunner


class BackendRegistry:
    """
    Central coordinator for quantum execution backends.
    """

    def __init__(self):
        self._qiskit_runner = QiskitAerRunner()
        self._cirq_runner = CirqRunner()
        self._pennylane_runner = PennyLaneRunner()
        self._qbraid_runner = QBraidRunner(fallback_runner=self._qiskit_runner)

        self._runners: Dict[str, QuantumBackendRunner] = {
            BackendType.QISKIT_AER.value: self._qiskit_runner,
            BackendType.CIRQ.value: self._cirq_runner,
            BackendType.PENNYLANE.value: self._pennylane_runner,
            BackendType.QBRAID.value: self._qbraid_runner,
        }

    def list_backends(self) -> List[BackendInfo]:
        """
        Returns the catalog of all available quantum backends.
        """
        backends: List[BackendInfo] = [
            BackendInfo(
                id=BackendType.LOCAL_CLIENT.value,
                name="Local In-Browser Engine",
                provider="Qual.dev Client",
                framework="Pure Vector Unitary",
                status=BackendStatus.AVAILABLE,
                version="2.0.0",
                description="Ultra-low latency in-browser quantum engine running real-time 2^n statevector calculations without server round-trips.",
                max_qubits=10,
                is_cloud=False,
                badge_color="cyan",
                icon="zap",
                features=[
                    "Zero network latency",
                    "Instant real-time synchronization",
                    "Continuous Bloch coordinates",
                    "No server computation cost",
                ],
            )
        ]

        for runner in self._runners.values():
            try:
                backends.append(runner.get_info())
            except Exception as e:
                print(f"Error fetching backend info: {e}")

        return backends

    def get_runner(self, backend_id: str) -> QuantumBackendRunner:
        runner = self._runners.get(backend_id)
        if not runner:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported backend '{backend_id}'. Available backends: {list(self._runners.keys())}",
            )
        return runner

    async def execute_circuit(self, request: SimulationRequest) -> SimulationResponse:
        """
        Routes the simulation request to the chosen backend runner.
        """
        backend_key = request.backend.value if hasattr(request.backend, "value") else str(request.backend)

        # If client requested client-side simulation on the server, default to Qiskit Aer
        if backend_key == BackendType.LOCAL_CLIENT.value:
            backend_key = BackendType.QISKIT_AER.value

        runner = self.get_runner(backend_key)
        return await runner.execute(request.circuit, shots=request.shots, **(request.options or {}))

    def transpile_circuit(self, request: TranspileRequest) -> TranspileResponse:
        """
        Converts the circuit into executable code for the target framework.
        """
        target = request.target_framework.lower().strip()
        if target in ("qiskit", "qiskit_aer", "python"):
            code = self._qiskit_runner.transpile_code(request.circuit)
        elif target in ("cirq", "google"):
            code = self._cirq_runner.transpile_code(request.circuit)
        elif target in ("pennylane", "qml"):
            code = self._pennylane_runner.transpile_code(request.circuit)
        elif target in ("qbraid", "multicloud"):
            code = self._qbraid_runner.transpile_code(request.circuit)
        else:
            code = self._qiskit_runner.transpile_code(request.circuit)

        return TranspileResponse(
            success=True,
            target_framework=target,
            code=code,
        )


backend_registry = BackendRegistry()
