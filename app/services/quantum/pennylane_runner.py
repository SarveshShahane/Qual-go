import math
import time
from typing import Dict, List, Optional
import numpy as np

import pennylane as qml

from app.schemas.quantum import (
    BackendInfo,
    BackendStatus,
    CanonicalCircuit,
    SimulationResponse,
)
from app.services.quantum.base_backend import QuantumBackendRunner


class PennyLaneRunner(QuantumBackendRunner):
    """
    Xanadu PennyLane runner utilizing default.qubit and lightning device simulators.
    """

    def __init__(self):
        self._version = qml.__version__

    def get_info(self) -> BackendInfo:
        return BackendInfo(
            id="pennylane",
            name="PennyLane Differentiable Simulator",
            provider="Xanadu",
            framework="PennyLane",
            status=BackendStatus.AVAILABLE,
            version=f"PennyLane {self._version}",
            description="Quantum machine learning and differentiable quantum computing platform supporting analytic gradients and hybrid quantum-classical pipelines.",
            max_qubits=24,
            is_cloud=False,
            badge_color="rose",
            icon="pennylane",
            features=[
                "Differentiable quantum computing",
                "Hybrid quantum-classical optimization",
                "Automatic differentiation (autograd/jax/torch)",
                "Full statevector inspection",
                "Bloch vector extraction",
            ],
        )

    def _apply_gates(self, circuit: CanonicalCircuit, num_qubits: int):
        for moment in circuit.moments:
            for op in moment.operations:
                gate = op.gate.upper()
                targets = op.targets
                controls = op.controls or []
                params = op.params or []

                t0 = targets[0] if targets and targets[0] < num_qubits else 0

                if gate == "H":
                    qml.Hadamard(wires=t0)
                elif gate == "X":
                    qml.PauliX(wires=t0)
                elif gate == "Y":
                    qml.PauliY(wires=t0)
                elif gate == "Z":
                    qml.PauliZ(wires=t0)
                elif gate == "S":
                    qml.S(wires=t0)
                elif gate == "T":
                    qml.T(wires=t0)
                elif gate == "SX":
                    qml.SX(wires=t0)
                elif gate == "RX":
                    theta = params[0] if params else math.pi / 2
                    qml.RX(theta, wires=t0)
                elif gate == "RY":
                    theta = params[0] if params else math.pi / 2
                    qml.RY(theta, wires=t0)
                elif gate == "RZ":
                    theta = params[0] if params else math.pi / 2
                    qml.RZ(theta, wires=t0)
                elif gate in ("CX", "CNOT"):
                    c0 = controls[0] if controls and controls[0] < num_qubits else 0
                    qml.CNOT(wires=[c0, t0])
                elif gate == "CZ":
                    c0 = controls[0] if controls and controls[0] < num_qubits else 0
                    qml.CZ(wires=[c0, t0])
                elif gate == "SWAP":
                    t1 = targets[1] if len(targets) > 1 and targets[1] < num_qubits else (t0 + 1) % num_qubits
                    qml.SWAP(wires=[t0, t1])
                elif gate in ("CCX", "TOFFOLI"):
                    c0 = controls[0] if len(controls) > 0 and controls[0] < num_qubits else 0
                    c1 = controls[1] if len(controls) > 1 and controls[1] < num_qubits else 1
                    qml.Toffoli(wires=[c0, c1, t0])
                elif gate == "BARRIER":
                    qml.Barrier(wires=range(num_qubits))

    async def execute(self, circuit: CanonicalCircuit, shots: int = 1024, **kwargs) -> SimulationResponse:
        start_time = time.perf_counter()
        num_qubits = max(1, circuit.qubits)

        # 1. Statevector QNode
        dev_analytic = qml.device("default.qubit", wires=num_qubits)

        @qml.qnode(dev_analytic)
        def state_circuit():
            self._apply_gates(circuit, num_qubits)
            return qml.state()

        sv_raw = state_circuit()
        sv_data = np.asarray(sv_raw, dtype=np.complex128)

        statevector_items, probabilities = self.format_statevector(sv_data, circuit.qubits)
        bloch_vectors = self.compute_bloch_vectors(sv_data, circuit.qubits)

        # 2. Shot sampling QNode
        dev_shots = qml.device("default.qubit", wires=num_qubits, shots=shots)

        @qml.qnode(dev_shots)
        def sample_circuit():
            self._apply_gates(circuit, num_qubits)
            return qml.counts(all_outcomes=True)

        raw_counts = sample_circuit()
        counts: Dict[str, int] = {}
        for bitstr, cnt in raw_counts.items():
            clean_str = str(bitstr).strip()
            counts[clean_str] = int(cnt)

        # Generate PennyLane draw
        try:
            drawer = qml.draw(state_circuit)
            circuit_diagram = drawer()
        except Exception:
            circuit_diagram = None

        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return SimulationResponse(
            backend="pennylane",
            backend_name="PennyLane Differentiable Simulator",
            framework="PennyLane",
            framework_version=self._version,
            shots=shots,
            qubits=circuit.qubits,
            executionTimeMs=execution_time_ms,
            probabilities=probabilities,
            counts=counts,
            statevector=statevector_items,
            blochVectors=bloch_vectors,
            circuitDiagram=circuit_diagram,
            transpiledCode=self.transpile_code(circuit),
            metadata={
                "device": "default.qubit",
                "shots": shots,
                "differentiable": True,
            },
        )

    def transpile_code(self, circuit: CanonicalCircuit) -> str:
        lines: List[str] = [
            "# Generated by Qual.dev PennyLane Transpiler",
            "import pennylane as qml",
            "",
            f"dev = qml.device('default.qubit', wires={circuit.qubits})",
            "",
            "@qml.qnode(dev)",
            "def quantum_circuit():",
        ]

        has_any_gate = False
        for moment in circuit.moments:
            for op in moment.operations:
                has_any_gate = True
                g = op.gate.upper()
                t = op.targets[0] if op.targets else 0
                c = op.controls or []
                p = op.params or []

                if g == "H": lines.append(f"    qml.Hadamard(wires={t})")
                elif g == "X": lines.append(f"    qml.PauliX(wires={t})")
                elif g == "Y": lines.append(f"    qml.PauliY(wires={t})")
                elif g == "Z": lines.append(f"    qml.PauliZ(wires={t})")
                elif g == "S": lines.append(f"    qml.S(wires={t})")
                elif g == "T": lines.append(f"    qml.T(wires={t})")
                elif g == "SX": lines.append(f"    qml.SX(wires={t})")
                elif g == "RX": lines.append(f"    qml.RX({p[0] if p else '3.14159/2'}, wires={t})")
                elif g == "RY": lines.append(f"    qml.RY({p[0] if p else '3.14159/2'}, wires={t})")
                elif g == "RZ": lines.append(f"    qml.RZ({p[0] if p else '3.14159/2'}, wires={t})")
                elif g in ("CX", "CNOT"): lines.append(f"    qml.CNOT(wires=[{c[0] if c else 0}, {t}])")
                elif g == "CZ": lines.append(f"    qml.CZ(wires=[{c[0] if c else 0}, {t}])")
                elif g == "SWAP": lines.append(f"    qml.SWAP(wires=[{t}, {op.targets[1] if len(op.targets) > 1 else 1}])")
                elif g in ("CCX", "TOFFOLI"): lines.append(f"    qml.Toffoli(wires=[{c[0] if len(c) > 0 else 0}, {c[1] if len(c) > 1 else 1}, {t}])")
                elif g == "BARRIER": lines.append(f"    qml.Barrier(wires=range({circuit.qubits}))")

        if not has_any_gate:
            lines.append("    pass")

        lines.append("    return qml.state()")
        lines.append("")
        lines.append("print(qml.draw(quantum_circuit)())")
        lines.append("state = quantum_circuit()")
        lines.append("print('Final Statevector:', state)")
        return "\n".join(lines)
