"""Health check endpoint."""

from fastapi import APIRouter

from backend.services.neo4j_client import Neo4jClient
from backend.services.ollama_client import OllamaClient
from backend.services.audio_service import AudioService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """
    Health check endpoint that returns the status of all services.

    Returns:
        dict: Status of each service (neo4j, ollama, audio)
    """
    # Get service instances
    neo4j_client = Neo4jClient.get_instance()
    ollama_client = OllamaClient.get_instance()
    audio_service = AudioService.get_instance()

    # Check Neo4j connection
    neo4j_status = await neo4j_client.health_check()

    # Check Ollama connection
    ollama_status = await ollama_client.health_check()

    # Check audio service
    audio_status = audio_service.health_check()

    # Overall status
    overall_status = (
        "healthy"
        if all(
            [
                neo4j_status["status"] == "healthy",
                ollama_status["status"] == "healthy",
                audio_status["status"] in ["healthy", "disabled"],
            ]
        )
        else "degraded"
    )

    return {
        "status": overall_status,
        "services": {
            "neo4j": neo4j_status,
            "ollama": ollama_status,
            "audio": audio_status,
        },
    }

