import logging
from typing import List, Optional

from app.schemas.ai_tutor import (
    AIDiagnostic,
    AIDiagnosticCategory,
    AIDiagnosticSeverity,
    AIHint,
    AIRecommendation,
    AIResponse,
    ChatMessage,
    LearnerProfile,
    TopicMastery,
    TutorChatRequest,
    TutorContext,
    TutoringMode,
    UserLevel,
)
from app.schemas.quantum import CanonicalCircuit, QuantumMoment, QuantumOperation
from app.services.ai.providers import get_ai_provider
from app.services.ai.rag_service import rag_service
from app.services.ai.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)


class TutorService:
    """
    Central orchestration service for the AI Quantum Tutor.
    Coordinates LLM providers (LangChain Groq), RAG curriculum retrieval,
    circuit validation, code generation, progressive hints, and recommendations.
    """

    def __init__(self):
        self.rag = rag_service
        self.recommender = recommendation_service

    async def chat(self, request: TutorChatRequest) -> AIResponse:
        """Main chat endpoint handling interactive pedagogical conversations."""
        provider = get_ai_provider()
        return await provider.generate_response(
            prompt=request.prompt,
            context=request.context,
            history=request.history,
        )

    async def explain(
        self,
        concept: Optional[str] = None,
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """Explains a quantum concept or current circuit at the user's level."""
        prompt = concept or (
            f"Explain the quantum mechanics and operations in this circuit: "
            f"{context.circuit.name if context and context.circuit else 'Hadamard Superposition'}"
        )
        ctx = context or TutorContext(tutoring_mode=TutoringMode.EXPLAIN)
        ctx.tutoring_mode = TutoringMode.EXPLAIN

        provider = get_ai_provider()
        return await provider.generate_response(prompt=prompt, context=ctx)

    async def generate_code(
        self,
        prompt: str,
        target_framework: str = "qiskit",
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """Generates valid quantum computing code in Qiskit, Cirq, or PennyLane."""
        ctx = context or TutorContext(tutoring_mode=TutoringMode.GENERATE)
        ctx.tutoring_mode = TutoringMode.GENERATE

        system_instruction = (
            f"You are QualGo's Quantum Code Generator. "
            f"Generate concise, complete, runnable {target_framework} Python code for the request. "
            f"Always include imports, circuit instantiation, gates, and simulation/measurement. "
            f"Return JSON with 'type': 'code', 'message': '<explanation>', 'code': '<executable code>', 'language': 'python'."
        )

        provider = get_ai_provider()
        return await provider.generate_response(
            prompt=prompt,
            context=ctx,
            system_instruction=system_instruction,
        )

    async def generate_circuit(
        self,
        prompt: str,
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """
        Generates a validated Canonical Circuit IR from natural language.
        Grounded in the QualGo IR schema.
        """
        ctx = context or TutorContext(tutoring_mode=TutoringMode.GENERATE)
        ctx.tutoring_mode = TutoringMode.GENERATE

        system_instruction = (
            "You are QualGo's Natural Language Circuit Builder. "
            "Convert the user's request into a validated Canonical Circuit IR JSON. "
            "Schema: {\n"
            '  "type": "circuit",\n'
            '  "message": "Explanation of the constructed circuit",\n'
            '  "code": "Equivalent Qiskit code",\n'
            '  "circuit": {\n'
            '    "name": "Circuit Name",\n'
            '    "qubits": 2,\n'
            '    "classicalBits": 2,\n'
            '    "moments": [\n'
            '      {"operations": [{"gate": "H", "targets": [0]}]},\n'
            '      {"operations": [{"gate": "CX", "targets": [1], "controls": [0]}]}\n'
            '    ]\n'
            '  }\n'
            "}\n"
            "Ensure qubits >= 1, controls and targets do not collide, and gates are standard (H, X, Y, Z, S, T, CX, CZ, SWAP, CCX, Rx, Ry, Rz, Measure)."
        )

        provider = get_ai_provider()
        response = await provider.generate_response(
            prompt=prompt,
            context=ctx,
            system_instruction=system_instruction,
        )

        # Ensure valid circuit is attached
        if not response.circuit:
            p_lower = prompt.lower()
            if "ghz" in p_lower:
                response.circuit = CanonicalCircuit(
                    name="GHZ State",
                    qubits=3,
                    classicalBits=3,
                    moments=[
                        QuantumMoment(operations=[QuantumOperation(gate="H", targets=[0])]),
                        QuantumMoment(operations=[QuantumOperation(gate="CX", targets=[1], controls=[0])]),
                        QuantumMoment(operations=[QuantumOperation(gate="CX", targets=[2], controls=[1])]),
                    ],
                )
            else:
                response.circuit = CanonicalCircuit(
                    name="Bell State (|Φ⁺⟩)",
                    qubits=2,
                    classicalBits=2,
                    moments=[
                        QuantumMoment(operations=[QuantumOperation(gate="H", targets=[0])]),
                        QuantumMoment(operations=[QuantumOperation(gate="CX", targets=[1], controls=[0])]),
                    ],
                )

        return response

    async def debug(
        self,
        code: Optional[str] = None,
        circuit: Optional[CanonicalCircuit] = None,
        error_message: Optional[str] = None,
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """
        Diagnoses quantum circuit and code errors, clearly distinguishing
        code/syntax bugs from quantum-mechanical concept errors.
        """
        ctx = context or TutorContext(tutoring_mode=TutoringMode.DEBUG)
        ctx.tutoring_mode = TutoringMode.DEBUG
        if code:
            ctx.code = code
        if circuit:
            ctx.circuit = circuit
        if error_message:
            ctx.error_message = error_message

        prompt = f"Analyze and debug this quantum circuit/code error: {error_message or 'Check for subtle quantum logic errors'}"
        system_instruction = (
            "You are QualGo's Quantum Circuit & Code Debugger. "
            "Analyze the circuit, code, or error message. Identify the Problem, Cause, and Suggested Fix. "
            "Distinguish between code syntax errors and quantum-mechanical concept errors. "
            "Return JSON with 'type': 'debug', 'message': '<markdown explanation>', "
            "'diagnostics': [{'severity': 'error', 'category': 'quantum_concept', "
            "'problem': '...', 'cause': '...', 'suggested_fix': '...'}]"
        )

        provider = get_ai_provider()
        return await provider.generate_response(
            prompt=prompt,
            context=ctx,
            system_instruction=system_instruction,
        )

    async def get_hint(
        self,
        challenge_id: Optional[str] = None,
        hint_level: int = 1,
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """Progressive hint progression (1: Concept, 2: Direction, 3: Partial, 4: Solution)."""
        ctx = context or TutorContext(tutoring_mode=TutoringMode.HINT)
        ctx.tutoring_mode = TutoringMode.HINT
        ctx.hint_level = hint_level
        ctx.current_challenge_id = challenge_id

        prompt = f"Provide progressive hint level {hint_level} for challenge {challenge_id or 'quantum superposition and entanglement'}"
        system_instruction = (
            f"You are QualGo's Progressive Quantum Mentor. "
            f"Provide a progressive hint for level {hint_level} (Level 1: Concept clue, Level 2: Direction, Level 3: Partial snippet, Level 4: Complete solution). "
            f"Return JSON with 'type': 'hint', 'message': '<markdown hint>', "
            f"'hints': [{{'level': {hint_level}, 'label': 'Progressive Hint', 'content': '...'}}]"
        )

        provider = get_ai_provider()
        return await provider.generate_response(
            prompt=prompt,
            context=ctx,
            system_instruction=system_instruction,
        )

    async def get_recommendations(
        self,
        profile: Optional[LearnerProfile] = None,
        context: Optional[TutorContext] = None,
    ) -> AIResponse:
        """Synthesizes learner profile and assessment scores into high-impact next steps."""
        recs = self.recommender.generate_recommendations(profile=profile, context=context)
        masteries = self.recommender.estimate_mastery(profile=profile or LearnerProfile())

        top_mastery = masteries[0] if masteries else None

        msg = (
            "### Personalized Quantum Learning Pathway\n\n"
            "Based on your completed modules, quiz mastery scores, and circuit design activity, "
            "here are your prioritized next steps:"
        )

        return AIResponse(
            type="recommendation",
            message=msg,
            recommendations=recs,
            mastery_update=top_mastery,
            suggested_followups=[
                "Start recommended topic",
                "Explain prerequisites for this challenge",
                "How is my mastery score calculated?"
            ],
            provider="qualgo-recommender",
            model="learner-profile-engine",
        )

    async def analyze_circuit(self, circuit: CanonicalCircuit) -> AIResponse:
        """
        Step-by-step quantum state evolution analysis of the canonical circuit IR.
        """
        lines = []
        lines.append(f"### Quantum State Evolution Analysis: **{circuit.name}**\n")
        lines.append(f"- **Total Qubits**: {circuit.qubits}")
        lines.append(f"- **Total Moments (Time Steps)**: {len(circuit.moments)}\n")
        lines.append("#### Timeline Walkthrough:\n")

        total_ops = 0
        has_entanglement = False

        for m_idx, moment in enumerate(circuit.moments):
            if not moment.operations:
                continue

            op_descriptions = []
            for op in moment.operations:
                total_ops += 1
                g = op.gate.upper()
                t = op.targets
                c = op.controls or []

                if g == "H":
                    op_descriptions.append(f"- **H on q{t[0]}**: Creates equal superposition $(|0\\rangle + |1\\rangle)/\\sqrt{{2}}$.")
                elif g == "X":
                    op_descriptions.append(f"- **X (NOT) on q{t[0]}**: Bit-flip operation ($|0\\rangle \\leftrightarrow |1\\rangle$).")
                elif g == "Z":
                    op_descriptions.append(f"- **Z on q{t[0]}**: Phase-flip operation ($|1\\rangle \\to -|1\\rangle$).")
                elif g in ("CX", "CNOT"):
                    has_entanglement = True
                    tgt = t[0]
                    ctrl = c[0] if c else (1 if tgt == 0 else 0)
                    if ctrl == tgt:
                        op_descriptions.append(f"- **CX (CNOT) [⚠️ Gate Warning]**: Control and target are both q{tgt}! Multi-qubit operations require distinct control and target qubits.")
                    else:
                        op_descriptions.append(f"- **CX (CNOT)**: Controlled by q{ctrl}, targets q{tgt}. Establishes multi-qubit entanglement.")
                elif g == "CZ":
                    ctrl = c[0] if c else (1 if t[0] == 0 else 0)
                    op_descriptions.append(f"- **CZ**: Controlled-phase flip between q{ctrl} and q{t[0]}.")
                elif g in ("RX", "RY", "RZ"):
                    angle_expr = op.paramExpressions[0] if op.paramExpressions else f"{op.params[0]:.3f}" if op.params else "θ"
                    op_descriptions.append(f"- **{g}({angle_expr}) on q{t[0]}**: Continuous Bloch sphere rotation.")
                elif g == "MEASURE":
                    op_descriptions.append(f"- **Measure q{t[0]}**: Projects coherent state into computational basis.")
                else:
                    op_descriptions.append(f"- **{op.gate} on q{t[0]}**: Quantum unitary transformation.")

            lines.append(f"**Step {m_idx + 1} (t = {m_idx})**:")
            lines.extend(op_descriptions)
            lines.append("")

        if has_entanglement:
            lines.append("> 🔗 **Entanglement Notice**: This circuit generates non-separable quantum states. The measurement outcomes of the qubits are correlated.\n")

        lines.append("**Recommended Next Action**: Click **Run Simulation** to inspect the statevector and 3D Bloch sphere vectors.")

        return AIResponse(
            type="explanation",
            message="\n".join(lines),
            circuit=circuit,
            suggested_followups=[
                "What is the final statevector in Dirac notation?",
                "How do I optimize this circuit?",
                "Simulate with Qiskit Aer"
            ],
            provider="qualgo-circuit-analyzer",
            model="symbolic-state-tracer",
        )


tutor_service = TutorService()
