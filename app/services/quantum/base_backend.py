import abc
import math
from typing import Dict, List, Tuple
import numpy as np

from app.schemas.quantum import (
    BackendInfo,
    BlochVector,
    CanonicalCircuit,
    SimulationResponse,
    StatevectorItem,
)


class QuantumBackendRunner(abc.ABC):
    """
    Abstract interface for all quantum simulation and execution backends.
    """

    @abc.abstractmethod
    def get_info(self) -> BackendInfo:
        """Returns metadata and live status of this quantum backend."""
        pass

    @abc.abstractmethod
    async def execute(self, circuit: CanonicalCircuit, shots: int = 1024, **kwargs) -> SimulationResponse:
        """Simulates or executes the canonical quantum circuit."""
        pass

    @abc.abstractmethod
    def transpile_code(self, circuit: CanonicalCircuit) -> str:
        """Generates framework-native executable code representation."""
        pass

    @staticmethod
    def compute_bloch_vectors(statevector: np.ndarray, num_qubits: int) -> List[BlochVector]:
        """
        Computes the single-qubit Bloch vector (x, y, z) for each qubit
        by tracing out all other qubits from the pure statevector.
        """
        bloch_vectors: List[BlochVector] = []
        dim = 1 << num_qubits

        for q in range(num_qubits):
            # Compute reduced density matrix elements: rho_00, rho_01, rho_10, rho_11
            # Convention: qubit 0 is bit 0 (least significant bit)
            mask = 1 << q

            rho_00 = 0.0
            rho_11 = 0.0
            rho_01 = 0.0 + 0.0j

            for i in range(dim):
                if (i & mask) == 0:
                    j = i | mask
                    c0 = statevector[i]
                    c1 = statevector[j]

                    rho_00 += float(np.abs(c0) ** 2)
                    rho_11 += float(np.abs(c1) ** 2)
                    rho_01 += c0 * np.conj(c1)

            x = float(2.0 * np.real(rho_01))
            y = float(-2.0 * np.imag(rho_01))
            z = float(rho_00 - rho_11)

            bloch_vectors.append(
                BlochVector(
                    qubit=q,
                    x=round(x, 4),
                    y=round(y, 4),
                    z=round(z, 4),
                )
            )

        return bloch_vectors

    @staticmethod
    def format_statevector(statevector: np.ndarray, num_qubits: int, threshold: float = 1e-6) -> Tuple[List[StatevectorItem], Dict[str, float]]:
        """
        Builds friendly basis-state telemetry and exact Born probability distribution.
        """
        items: List[StatevectorItem] = []
        probabilities: Dict[str, float] = {}
        dim = len(statevector)

        for i in range(dim):
            # In standard Qiskit / physics representation, qubit 0 is the rightmost digit:
            bitstr = format(i, f"0{num_qubits}b")
            amp = statevector[i]
            real = float(np.real(amp))
            imag = float(np.imag(amp))
            prob = float(real**2 + imag**2)
            probabilities[bitstr] = round(prob, 6)

            mag = float(np.abs(amp))
            phase_rad = float(np.angle(amp))
            phase_deg = float(math.degrees(phase_rad))
            if phase_deg < 0:
                phase_deg += 360.0

            items.append(
                StatevectorItem(
                    basisState=f"|{bitstr}⟩",
                    index=i,
                    real=round(real, 6),
                    imag=round(imag, 6),
                    magnitude=round(mag, 6),
                    probability=round(prob, 6),
                    phaseRadians=round(phase_rad, 6),
                    phaseDegrees=round(phase_deg, 2),
                )
            )

        return items, probabilities
