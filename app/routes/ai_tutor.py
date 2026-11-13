import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.ai_tutor import (
    AIResponse,
    DebugRequest,
    ExplainRequest,
    GenerateCircuitRequest,
    GenerateCodeRequest,
    HintRequest,
    RecommendationRequest,
    TutorChatRequest,
    TutorContext,
)
from app.schemas.quantum import CanonicalCircuit
from app.services.ai.tutor_service import TutorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["AI Quantum Tutor"])
tutor_service = TutorService()


@router.post("/ai/chat", response_model=AIResponse)
async def chat_with_tutor(request: TutorChatRequest):
    """
    Main interactive chat with the AI Quantum Tutor.
    Grounded in QualGo course material with LangChain Groq + fallback.
    """
    try:
        response = await tutor_service.chat(request)
        return response
    except Exception as e:
        logger.error(f"Error in tutor chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Tutor chat failed: {str(e)}",
        )


@router.post("/ai/explain", response_model=AIResponse)
async def explain_concept(request: ExplainRequest):
    """
    Explains quantum computing concepts or active circuits adapted
    to the user's expertise level (beginner/intermediate/advanced).
    """
    try:
        response = await tutor_service.explain(
            concept=request.concept,
            context=request.context,
        )
        return response
    except Exception as e:
        logger.error(f"Error in concept explanation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Concept explanation failed: {str(e)}",
        )


@router.post("/ai/generate-code", response_model=AIResponse)
async def generate_code(request: GenerateCodeRequest):
    """
    Generates runnable quantum computing code (Qiskit, Cirq, PennyLane)
    from natural language instructions.
    """
    try:
        response = await tutor_service.generate_code(
            prompt=request.prompt,
            target_framework=request.target_framework,
            context=request.context,
        )
        return response
    except Exception as e:
        logger.error(f"Error in code generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code generation failed: {str(e)}",
        )


@router.post("/ai/generate-circuit", response_model=AIResponse)
async def generate_circuit(request: GenerateCircuitRequest):
    """
    Generates validated Canonical Circuit IR from natural language.
    Validates structure before returning to prevent canvas corruption.
    """
    try:
        response = await tutor_service.generate_circuit(
            prompt=request.prompt,
            context=request.context,
        )
        return response
    except Exception as e:
        logger.error(f"Error in circuit generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Circuit generation failed: {str(e)}",
        )


@router.post("/ai/debug", response_model=AIResponse)
async def debug_circuit_or_code(request: DebugRequest):
    """
    Diagnoses quantum circuit or code errors, clearly separating
    syntax/programming bugs from fundamental quantum concept misunderstandings.
    """
    try:
        ctx = request.context or TutorContext()
        if request.simulation_result:
            ctx.simulation_result = request.simulation_result

        response = await tutor_service.debug(
            code=request.code,
            circuit=request.circuit,
            error_message=request.error_message,
            context=ctx,
        )
        return response
    except Exception as e:
        logger.error(f"Error in debugging: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debugging failed: {str(e)}",
        )


@router.post("/ai/hint", response_model=AIResponse)
async def get_progressive_hint(request: HintRequest):
    """
    Returns progressive pedagogical hints:
    Level 1: Concept Clue -> Level 2: Direction -> Level 3: Partial Snippet -> Level 4: Full Solution.
    """
    try:
        response = await tutor_service.get_hint(
            challenge_id=request.challenge_id,
            hint_level=request.hint_level,
            context=request.context,
        )
        return response
    except Exception as e:
        logger.error(f"Error in hint retrieval: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hint retrieval failed: {str(e)}",
        )


@router.post("/ai/recommendations", response_model=AIResponse)
async def get_personalized_recommendations(request: RecommendationRequest):
    """
    Calculates topic mastery and returns prioritized next steps and learning pathway recommendations.
    """
    try:
        response = await tutor_service.get_recommendations(
            profile=request.profile,
            context=request.context,
        )
        return response
    except Exception as e:
        logger.error(f"Error in recommendation generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendations failed: {str(e)}",
        )


@router.post("/ai/analyze-circuit", response_model=AIResponse)
async def analyze_circuit(circuit: CanonicalCircuit):
    """
    Performs step-by-step quantum state evolution analysis of the circuit moments.
    """
    try:
        response = await tutor_service.analyze_circuit(circuit)
        return response
    except Exception as e:
        logger.error(f"Error in circuit analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Circuit analysis failed: {str(e)}",
        )
