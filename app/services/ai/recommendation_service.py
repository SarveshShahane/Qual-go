from typing import Dict, List, Optional
from app.schemas.ai_tutor import (
    AIRecommendation,
    LearnerProfile,
    TopicMastery,
    TutorContext,
)


class RecommendationService:
    """
    Personalized learning recommendation and mastery estimation engine
    grounded in QualGo's curriculum structure.
    """

    CURRICULUM_TOPIC_MAP = {
        "vectors": {"name": "Vectors in Quantum Mechanics", "module": "Mathematics", "chapter": "01-vectors", "difficulty": "Beginner"},
        "vector-notation": {"name": "Vector Notation & Spaces", "module": "Mathematics", "chapter": "02-vector-notation", "difficulty": "Beginner"},
        "complex-numbers": {"name": "Complex Numbers & Modulus", "module": "Mathematics", "chapter": "03-complex-numbers", "difficulty": "Beginner"},
        "probability": {"name": "Classical Probability Distributions", "module": "Mathematics", "chapter": "04-probability", "difficulty": "Beginner"},
        "probability-amplitudes": {"name": "Quantum Probability Amplitudes", "module": "Mathematics", "chapter": "05-probability-amplitudes", "difficulty": "Intermediate"},
        "normalization": {"name": "State Normalization Constraint", "module": "Mathematics", "chapter": "06-normalization", "difficulty": "Intermediate"},
        "matrices": {"name": "Linear Operators & Matrices", "module": "Mathematics", "chapter": "07-matrices", "difficulty": "Intermediate"},
        "matrix-vector-multiplication": {"name": "Matrix-Vector Transformations", "module": "Mathematics", "chapter": "08-matrix-vector-multiplication", "difficulty": "Intermediate"},
        "unitary-matrices": {"name": "Unitary Matrices & Preserving Norms", "module": "Mathematics", "chapter": "09-unitary-matrices", "difficulty": "Advanced"},
        "dirac-notation": {"name": "Dirac Bra-Ket Formalism", "module": "Mathematics", "chapter": "10-dirac-notation", "difficulty": "Advanced"},
        "qubits": {"name": "Classical Bit vs Quantum Bit", "module": "Qubits", "chapter": "01-classical-bit-vs-qubit", "difficulty": "Beginner"},
        "computational-basis": {"name": "Computational Basis States |0⟩ & |1⟩", "module": "Qubits", "chapter": "02-computational-basis", "difficulty": "Beginner"},
        "general-qubit-state": {"name": "General Qubit State & Bloch Representation", "module": "Qubits", "chapter": "03-general-qubit-state", "difficulty": "Intermediate"},
        "phase": {"name": "Relative vs Global Phase", "module": "Qubits", "chapter": "04-phase", "difficulty": "Intermediate"},
        "superposition": {"name": "What is Quantum Superposition?", "module": "Superposition", "chapter": "01-what-is-superposition", "difficulty": "Beginner"},
        "hadamard-gate": {"name": "Hadamard Transformation", "module": "Superposition", "chapter": "02-hadamard-gate", "difficulty": "Beginner"},
        "measurement": {"name": "Quantum Measurement & Collapse", "module": "Superposition", "chapter": "03-measurement", "difficulty": "Intermediate"},
        "entanglement": {"name": "Quantum Entanglement & Bell States", "module": "Algorithms", "chapter": "01-bell-states", "difficulty": "Advanced"},
    }

    def estimate_mastery(self, profile: LearnerProfile) -> List[TopicMastery]:
        """
        Estimates mastery score (0.0 to 1.0) and confidence across curriculum topics.
        """
        masteries: List[TopicMastery] = []

        completed_set = set(profile.completed_topics)
        weak_set = set(profile.weak_topics)
        mistake_counts: Dict[str, int] = {}
        for m in profile.recent_mistakes:
            key = m.lower()
            mistake_counts[key] = mistake_counts.get(key, 0) + 1

        for topic_id, meta in self.CURRICULUM_TOPIC_MAP.items():
            base_score = 0.2
            confidence = 0.3

            if topic_id in completed_set:
                base_score += 0.5
                confidence += 0.4

            # Assessment scores
            if topic_id in profile.assessment_scores:
                score_val = profile.assessment_scores[topic_id]
                base_score = 0.4 * base_score + 0.6 * score_val
                confidence = min(1.0, confidence + 0.3)

            # Penalties for recurring mistakes
            if topic_id in weak_set:
                base_score = max(0.1, base_score - 0.25)

            # Hint dependency deduction
            if profile.hint_dependency_score > 0.5:
                base_score = max(0.15, base_score - 0.1)

            final_score = round(min(1.0, max(0.0, base_score)), 2)
            final_conf = round(min(1.0, max(0.1, confidence)), 2)

            if final_score >= 0.8:
                status = "mastered"
            elif final_score >= 0.45:
                status = "learning"
            else:
                status = "needs_review"

            masteries.append(TopicMastery(
                topic_id=topic_id,
                topic_name=meta["name"],
                score=final_score,
                confidence=final_conf,
                status=status,
            ))

        return masteries

    def generate_recommendations(
        self, profile: Optional[LearnerProfile] = None, context: Optional[TutorContext] = None
    ) -> List[AIRecommendation]:
        """
        Synthesizes student performance and context into high-impact next steps.
        """
        recs: List[AIRecommendation] = []
        completed = set(profile.completed_topics if profile else [])
        weak = set(profile.weak_topics if profile else [])

        # Priority 1: Address active weaknesses or mistakes
        if weak or (context and context.recent_mistakes):
            for w in weak:
                if w in self.CURRICULUM_TOPIC_MAP:
                    meta = self.CURRICULUM_TOPIC_MAP[w]
                    recs.append(AIRecommendation(
                        id=f"rec_weak_{w}",
                        title=f"Review & Practice: {meta['name']}",
                        reason="Identified as an area needing reinforcement based on recent quiz or circuit errors.",
                        target_module=meta["module"],
                        target_chapter=meta["chapter"],
                        difficulty=meta["difficulty"],
                        priority=1,
                    ))

        # Priority 2: Next uncompleted progressive topic
        ordered_keys = list(self.CURRICULUM_TOPIC_MAP.keys())
        for k in ordered_keys:
            if k not in completed:
                meta = self.CURRICULUM_TOPIC_MAP[k]
                recs.append(AIRecommendation(
                    id=f"rec_next_{k}",
                    title=f"Next in Curriculum: {meta['name']}",
                    reason="Logical progressive next topic in your quantum computing pathway.",
                    target_module=meta["module"],
                    target_chapter=meta["chapter"],
                    difficulty=meta["difficulty"],
                    priority=2,
                ))
                break

        # Priority 3: Interactive challenge recommendation
        recs.append(AIRecommendation(
            id="rec_challenge_bell_state",
            title="Challenge: Build Bell State in Circuit Studio",
            reason="Synthesize Hadamard and CNOT gates to observe maximal entanglement on the Bloch sphere.",
            target_module="Circuit Studio",
            target_chapter="Templates > Bell State",
            difficulty="Beginner",
            priority=3,
        ))

        recs.append(AIRecommendation(
            id="rec_multi_backend_sim",
            title="Benchmark: Run Qiskit vs Cirq vs PennyLane",
            reason="Compare statevector outputs and execution latencies across physical framework backends.",
            target_module="Circuit Studio",
            target_chapter="Compare Backends",
            difficulty="Intermediate",
            priority=4,
        ))

        return recs[:4]


recommendation_service = RecommendationService()
