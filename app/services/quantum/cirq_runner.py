import math
import time
from typing import Dict, List, Optional, Tuple
import numpy as np

import cirq

from app.schemas.quantum import (
    BackendInfo,
    BackendStatus,
    CanonicalCircuit,
    SimulationResponse,
)
from app.services.quantum.base_backend import QuantumBackendRunner


class CirqRunner(QuantumBackendRunner):
    """
    Google Cirq backend runner utilizing cirq.Simulator.
    """

    def __init__(self):
        self.simulator = cirq.Simulator()
        self._version = cirq.__version__

    def get_info(self) -> BackendInfo:
        return BackendInfo(
            id="cirq",
            name="Google Cirq Simulator",
            provider="Google Quantum AI",
            framework="Cirq",
            status=BackendStatus.AVAILABLE,
            version=f"Cirq {self._version}",
            description="Google Quantum AI framework optimized for NISQ quantum computer architectures, Sycamore processors, and wavefunction simulations.",
            max_qubits=20,
            is_cloud=False,
            badge_color="emerald",
            icon="cirq",
            features=[
                "Wavefunction simulation",
                "NISQ architecture mapping",
                "LineQubit and GridQubit topologies",
                "Density matrix simulation",
                "Bloch vector extraction",
            ],
        )

    def to_cirq_circuit(self, circuit: CanonicalCircuit, include_measurements: bool = True) -> Tuple[cirq.Circuit, List[cirq.LineQubit]]:
        num_qubits = max(1, circuit.qubits)
        qubits = cirq.LineQubit.range(num_qubits)
        cirq_circuit = cirq.Circuit()

        for moment in circuit.moments:
            moment_ops = []
            for op in moment.operations:
                gate = op.gate.upper()
                targets = op.targets
                controls = op.controls or []
                params = op.params or []

                t0 = targets[0] if targets and targets[0] < num_qubits else 0
                q_target = qubits[t0]

                if gate == "H":
                    moment_ops.append(cirq.H(q_target))
                elif gate == "X":
                    moment_ops.append(cirq.X(q_target))
                elif gate == "Y":
                    moment_ops.append(cirq.Y(q_target))
                elif gate == "Z":
                    moment_ops.append(cirq.Z(q_target))
                elif gate == "S":
                    moment_ops.append(cirq.S(q_target))
                elif gate == "T":
                    moment_ops.append(cirq.T(q_target))
                elif gate == "SX":
                    moment_ops.append(cirq.X(q_target) ** 0.5)
                elif gate == "RX":
                    theta = params[0] if params else math.pi / 2
                    moment_ops.append(cirq.rx(theta)(q_target))
                elif gate == "RY":
                    theta = params[0] if params else math.pi / 2
                    moment_ops.append(cirq.ry(theta)(q_target))
                elif gate == "RZ":
                    theta = params[0] if params else math.pi / 2
                    moment_ops.append(cirq.rz(theta)(q_target))
                elif gate in ("CX", "CNOT"):
                    c0 = controls[0] if controls and controls[0] < num_qubits else 0
                    moment_ops.append(cirq.CNOT(qubits[c0], q_target))
                elif gate == "CZ":
                    c0 = controls[0] if controls and controls[0] < num_qubits else 0
                    moment_ops.append(cirq.CZ(qubits[c0], q_target))
                elif gate == "SWAP":
                    t1 = targets[1] if len(targets) > 1 and targets[1] < num_qubits else (t0 + 1) % num_qubits
                    moment_ops.append(cirq.SWAP(qubits[t0], qubits[t1]))
                elif gate in ("CCX", "TOFFOLI"):
                    c0 = controls[0] if len(controls) > 0 and controls[0] < num_qubits else 0
                    c1 = controls[1] if len(controls) > 1 and controls[1] < num_qubits else 1
                    moment_ops.append(cirq.TOFFOLI(qubits[c0], qubits[c1], q_target))
                elif gate == "MEASURE" and include_measurements:
                    moment_ops.append(cirq.measure(q_target, key=f"q{t0}"))

            if moment_ops:
                cirq_circuit.append(moment_ops)

        return cirq_circuit, qubits

    async def execute(self, circuit: CanonicalCircuit, shots: int = 1024, **kwargs) -> SimulationResponse:
        start_time = time.perf_counter()

        # 1. Statevector computation (unmeasured)
        unitary_circuit, _ = self.to_cirq_circuit(circuit, include_measurements=False)
        sim_result = self.simulator.simulate(unitary_circuit)
        sv_data = np.asarray(sim_result.final_state_vector)

        statevector_items, probabilities = self.format_statevector(sv_data, circuit.qubits)
        bloch_vectors = self.compute_bloch_vectors(sv_data, circuit.qubits)

        # 2. Shot sampling
        measured_circuit, qubits = self.to_cirq_circuit(circuit, include_measurements=True)

        has_measure = any(
            op.gate.upper() == "MEASURE"
            for m in circuit.moments
            for op in m.operations
        )
        if not has_measure:
            measured_circuit.append([cirq.measure(q, key=f"q{idx}") for idx, q in enumerate(qubits)])

        run_result = self.simulator.run(measured_circuit, repetitions=shots)

        # Combine measurement keys into binary strings
        counts: Dict[str, int] = {}
        measurements_by_qubit = []
        for q_idx in range(circuit.qubits):
            key = f"q{q_idx}"
            if key in run_result.measurements:
                measurements_by_qubit.append(run_result.measurements[key].flatten())
            else:
                measurements_by_qubit.append(np.zeros(shots, dtype=int))

        for s in range(shots):
            # Standard order: q0 is rightmost bit (Qiskit/Cirq matching)
            bits = "".join(str(measurements_by_qubit[circuit.qubits - 1 - q_idx][s]) for q_idx in range(circuit.qubits))
            counts[bits] = counts.get(bits, 0) + 1

        # Cirq ASCII diagram
        try:
            circuit_diagram = str(measured_circuit)
        except Exception:
            circuit_diagram = None

        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return SimulationResponse(
            backend="cirq",
            backend_name="Google Cirq Simulator",
            framework="Cirq",
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
                "qubit_type": "LineQubit",
                "cirq_moments": len(measured_circuit),
                "shots": shots,
            },
        )

    def transpile_code(self, circuit: CanonicalCircuit) -> str:
        lines: List[str] = [
            "# Generated by Qual.dev Cirq Transpiler",
            "import cirq",
            "",
            f"qubits = cirq.LineQubit.range({circuit.qubits})",
            "circuit = cirq.Circuit()",
        ]

        for moment in circuit.moments:
            moment_ops = []
            for op in moment.operations:
                g = op.gate.upper()
                t = op.targets[0] if op.targets else 0
                c = op.controls or []
                p = op.params or []

                if g == "H": moment_ops.append(f"cirq.H(qubits[{t}])")
                elif g == "X": moment_ops.append(f"cirq.X(qubits[{t}])")
                elif g == "Y": moment_ops.append(f"cirq.Y(qubits[{t}])")
                elif g == "Z": moment_ops.append(f"cirq.Z(qubits[{t}])")
                elif g == "S": moment_ops.append(f"cirq.S(qubits[{t}])")
                elif g == "T": moment_ops.append(f"cirq.T(qubits[{t}])")
                elif g == "SX": moment_ops.append(f"cirq.X(qubits[{t}])**0.5")
                elif g == "RX": moment_ops.append(f"cirq.rx({p[0] if p else '3.14159/2'})(qubits[{t}])")
                elif g == "RY": moment_ops.append(f"cirq.ry({p[0] if p else '3.14159/2'})(qubits[{t}])")
                elif g == "RZ": moment_ops.append(f"cirq.rz({p[0] if p else '3.14159/2'})(qubits[{t}])")
                elif g in ("CX", "CNOT"): moment_ops.append(f"cirq.CNOT(qubits[{c[0] if c else 0}], qubits[{t}])")
                elif g == "CZ": moment_ops.append(f"cirq.CZ(qubits[{c[0] if c else 0}], qubits[{t}])")
                elif g == "SWAP": moment_ops.append(f"cirq.SWAP(qubits[{t}], qubits[{op.targets[1] if len(op.targets) > 1 else 1}])")
                elif g in ("CCX", "TOFFOLI"): moment_ops.append(f"cirq.TOFFOLI(qubits[{c[0] if len(c) > 0 else 0}], qubits[{c[1] if len(c) > 1 else 1}], qubits[{t}])")
                elif g == "MEASURE": moment_ops.append(f"cirq.measure(qubits[{t}], key='m{t}')")

            if moment_ops:
                lines.append(f"circuit.append([{', '.join(moment_ops)}])")

        lines.append("")
        lines.append("print(circuit)")
        lines.append("simulator = cirq.Simulator()")
        lines.append("result = simulator.run(circuit, repetitions=1024)")
        lines.append("print(result)")
        return "\n".join(lines)
