import math
import time
from typing import Dict, List, Optional
import numpy as np

import qiskit
import qiskit_aer
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from app.schemas.quantum import (
    BackendInfo,
    BackendStatus,
    CanonicalCircuit,
    SimulationResponse,
)
from app.services.quantum.base_backend import QuantumBackendRunner


class QiskitAerRunner(QuantumBackendRunner):
    """
    Qiskit Aer backend runner utilizing AerSimulator and statevector analysis.
    """

    def __init__(self):
        self.simulator = AerSimulator()
        self._version = qiskit.__version__
        self._aer_version = getattr(qiskit_aer, "__version__", "0.17.2")

    def get_info(self) -> BackendInfo:
        return BackendInfo(
            id="qiskit_aer",
            name="Qiskit Aer Simulator",
            provider="IBM Quantum",
            framework="Qiskit Aer",
            status=BackendStatus.AVAILABLE,
            version=f"Qiskit {self._version} / Aer {self._aer_version}",
            description="High-performance C++ simulator supporting statevector evolution, density matrix, and noisy Clifford/unitary shot sampling.",
            max_qubits=24,
            is_cloud=False,
            badge_color="sky",
            icon="qiskit",
            features=[
                "Statevector simulation",
                "Matrix product state",
                "Shot sampling up to 100k",
                "GPU acceleration capable",
                "Bloch vector extraction",
            ],
        )

    def to_qiskit_circuit(self, circuit: CanonicalCircuit, include_measurements: bool = True) -> qiskit.QuantumCircuit:
        num_qubits = max(1, circuit.qubits)
        num_clbits = circuit.classicalBits if circuit.classicalBits > 0 else num_qubits
        qc = qiskit.QuantumCircuit(num_qubits, num_clbits)

        for moment in circuit.moments:
            for op in moment.operations:
                gate = op.gate.upper()
                targets = op.targets
                controls = op.controls or []
                params = op.params or []

                t0 = targets[0] if targets else 0

                if gate == "H":
                    qc.h(t0)
                elif gate == "X":
                    qc.x(t0)
                elif gate == "Y":
                    qc.y(t0)
                elif gate == "Z":
                    qc.z(t0)
                elif gate == "S":
                    qc.s(t0)
                elif gate == "T":
                    qc.t(t0)
                elif gate == "SX":
                    qc.sx(t0)
                elif gate == "RX":
                    theta = params[0] if params else math.pi / 2
                    qc.rx(theta, t0)
                elif gate == "RY":
                    theta = params[0] if params else math.pi / 2
                    qc.ry(theta, t0)
                elif gate == "RZ":
                    theta = params[0] if params else math.pi / 2
                    qc.rz(theta, t0)
                elif gate in ("CX", "CNOT"):
                    c0 = controls[0] if controls else 0
                    qc.cx(c0, t0)
                elif gate == "CZ":
                    c0 = controls[0] if controls else 0
                    qc.cz(c0, t0)
                elif gate == "SWAP":
                    t1 = targets[1] if len(targets) > 1 else (t0 + 1) % num_qubits
                    qc.swap(t0, t1)
                elif gate in ("CCX", "TOFFOLI"):
                    c0 = controls[0] if len(controls) > 0 else 0
                    c1 = controls[1] if len(controls) > 1 else 1
                    qc.ccx(c0, c1, t0)
                elif gate == "MEASURE" and include_measurements:
                    c_target = op.metadata.get("classicalTarget", t0) if op.metadata else t0
                    if c_target < num_clbits:
                        qc.measure(t0, c_target)
                elif gate == "BARRIER":
                    qc.barrier()

        return qc

    async def execute(self, circuit: CanonicalCircuit, shots: int = 1024, **kwargs) -> SimulationResponse:
        start_time = time.perf_counter()

        # 1. Statevector computation (unmeasured pure state)
        unitary_qc = self.to_qiskit_circuit(circuit, include_measurements=False)
        sv = Statevector.from_instruction(unitary_qc)
        sv_data = np.asarray(sv.data)

        statevector_items, probabilities = self.format_statevector(sv_data, circuit.qubits)
        bloch_vectors = self.compute_bloch_vectors(sv_data, circuit.qubits)

        # 2. Shot sampling using Qiskit Aer
        measured_qc = self.to_qiskit_circuit(circuit, include_measurements=True)

        # If no explicit measure gates were in the circuit, add measurement to all qubits
        has_measure = any(
            op.gate.upper() == "MEASURE"
            for m in circuit.moments
            for op in m.operations
        )
        if not has_measure:
            measured_qc.measure_all()

        job = self.simulator.run(measured_qc, shots=shots)
        result = job.result()
        raw_counts = result.get_counts(measured_qc)

        # Standardize bitstring counts (reverse Qiskit spaces if any)
        counts: Dict[str, int] = {}
        for bitstr, cnt in raw_counts.items():
            clean_str = bitstr.replace(" ", "")
            # Ensure width matches qubits
            if len(clean_str) > circuit.qubits:
                clean_str = clean_str[-circuit.qubits:]
            elif len(clean_str) < circuit.qubits:
                clean_str = clean_str.zfill(circuit.qubits)
            counts[clean_str] = cnt

        # ASCII circuit diagram
        try:
            circuit_diagram = str(measured_qc.draw(output="text"))
        except Exception:
            circuit_diagram = None

        execution_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return SimulationResponse(
            backend="qiskit_aer",
            backend_name="Qiskit Aer Simulator",
            framework="Qiskit",
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
                "aer_version": self._aer_version,
                "simulator_method": "statevector",
                "shots": shots,
            },
        )

    def transpile_code(self, circuit: CanonicalCircuit) -> str:
        lines: List[str] = [
            "# Generated by Qual.dev Qiskit Transpiler",
            "from qiskit import QuantumCircuit",
            "import numpy as np",
            "",
            f"qc = QuantumCircuit({circuit.qubits}, {circuit.classicalBits})",
        ]

        for moment in circuit.moments:
            for op in moment.operations:
                g = op.gate.upper()
                t = op.targets[0] if op.targets else 0
                c = op.controls or []
                p = op.params or []

                if g == "H": lines.append(f"qc.h({t})")
                elif g == "X": lines.append(f"qc.x({t})")
                elif g == "Y": lines.append(f"qc.y({t})")
                elif g == "Z": lines.append(f"qc.z({t})")
                elif g == "S": lines.append(f"qc.s({t})")
                elif g == "T": lines.append(f"qc.t({t})")
                elif g == "SX": lines.append(f"qc.sx({t})")
                elif g == "RX": lines.append(f"qc.rx({p[0] if p else 'np.pi/2'}, {t})")
                elif g == "RY": lines.append(f"qc.ry({p[0] if p else 'np.pi/2'}, {t})")
                elif g == "RZ": lines.append(f"qc.rz({p[0] if p else 'np.pi/2'}, {t})")
                elif g in ("CX", "CNOT"): lines.append(f"qc.cx({c[0] if c else 0}, {t})")
                elif g == "CZ": lines.append(f"qc.cz({c[0] if c else 0}, {t})")
                elif g == "SWAP": lines.append(f"qc.swap({t}, {op.targets[1] if len(op.targets) > 1 else 1})")
                elif g in ("CCX", "TOFFOLI"): lines.append(f"qc.ccx({c[0] if len(c) > 0 else 0}, {c[1] if len(c) > 1 else 1}, {t})")
                elif g == "MEASURE":
                    target_c = op.metadata.get("classicalTarget", t) if op.metadata else t
                    lines.append(f"qc.measure({t}, {target_c})")
                elif g == "BARRIER": lines.append("qc.barrier()")

        lines.append("")
        lines.append("print(qc.draw(output='text'))")
        return "\n".join(lines)
