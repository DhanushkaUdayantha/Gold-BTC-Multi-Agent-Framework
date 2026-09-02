"""Abstract base class for AI Market Analysis providers."""
from abc import ABC, abstractmethod
from src.models.ai_analysis import MultiTimeframeTechnicalInput, AIAnalysisResponse


class BaseAIProvider(ABC):
    """Abstract interface for AI analysis providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def generate_analysis(self, input_data: MultiTimeframeTechnicalInput) -> AIAnalysisResponse:
        """Process multi-timeframe technical input and generate structured market analysis.

        Args:
            input_data: Multi-timeframe technical indicators for 5m, 15m, 1h, 1d.

        Returns:
            AIAnalysisResponse with market condition, bias, confidence, and factors.
        """
        pass
