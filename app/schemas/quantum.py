from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, AliasChoices


class BackendType(str, Enum):
    LOCAL_CLIENT = "client"
    QISKIT_AER = "qiskit_aer"
    CIRQ = "cirq"
    PENNYLANE = "pennylane"
    QBRAID = "qbraid"


class BackendStatus(str, Enum):
    AVAILABLE = "available"
    READY = "ready"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"


class BackendInfo(BaseModel):
    id: str
    name: str
    provider: str
    framework: str
    status: BackendStatus
    version: Optional[str] = None
    description: str
    max_qubits: int = 24
    is_cloud: bool = False
    badge_color: str = "cyan"
    icon: str = "cpu"
    features: List[str] = Field(default_factory=list)


class QuantumOperation(BaseModel):
    id: Optional[str] = None
    gate: str
    targets: List[int]
    controls: Optional[List[int]] = Field(default_factory=list)
    params: Optional[List[float]] = Field(default_factory=list)
    paramExpressions: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QuantumMoment(BaseModel):
    id: Optional[str] = None
    operations: List[QuantumOperation] = Field(default_factory=list)


class CanonicalCircuit(BaseModel):
    id: Optional[str] = None
    name: str = "Quantum Circuit"
    qubits: int = Field(default=2, ge=1, le=24)
    qubitLabels: Optional[List[str]] = None
    classicalBits: int = Field(default=2, ge=0, le=24)
    classicalBitLabels: Optional[List[str]] = None
    moments: List[QuantumMoment] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    circuit: CanonicalCircuit
    backend: BackendType = BackendType.QISKIT_AER
    shots: int = Field(default=1024, ge=1, le=100000)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StatevectorItem(BaseModel):
    basisState: str
    index: int
    real: float
    imag: float
    magnitude: float
    probability: float
    phaseRadians: float
    phaseDegrees: float


class BlochVector(BaseModel):
    qubit: int
    x: float
    y: float
    z: float


class SimulationResponse(BaseModel):
    success: bool = True
    backend: str = "qiskit_aer"
    backend_name: str = "Qiskit Aer"
    framework: str = "qiskit"
    framework_version: str = "1.0.0"
    shots: int = 1024
    qubits: int = 2
    executionTimeMs: float = Field(default=0.0, validation_alias=AliasChoices("executionTimeMs", "execution_time_ms"))
    probabilities: Dict[str, float] = Field(default_factory=dict)
    counts: Dict[str, int] = Field(default_factory=dict)
    statevector: Optional[List[StatevectorItem]] = None
    blochVectors: Optional[List[BlochVector]] = Field(default=None, validation_alias=AliasChoices("blochVectors", "bloch_vectors"))
    circuitDiagram: Optional[str] = Field(default=None, validation_alias=AliasChoices("circuitDiagram", "circuit_diagram"))
    transpiledCode: Optional[str] = Field(default=None, validation_alias=AliasChoices("transpiledCode", "transpiled_code"))
    metadata: Optional[Dict[str, Any]] = None


class TranspileRequest(BaseModel):
    circuit: CanonicalCircuit
    target_framework: str = Field(..., description="qiskit, cirq, pennylane, qbraid, qasm2, qasm3")


class TranspileResponse(BaseModel):
    success: bool = True
    source: str = "CanonicalCircuit"
    target_framework: str
    code: str
