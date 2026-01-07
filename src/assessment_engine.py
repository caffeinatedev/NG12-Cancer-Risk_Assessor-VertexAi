"""
Assessment engine for the NG12 Cancer Risk Assessor.
Provides clinical decision support logic for patient risk assessment.
"""
import logging
from typing import List, Optional, Dict, Any
import re

from .models import (
    PatientRecord, AssessmentRequest, AssessmentResponse, 
    Citation, RetrievedChunk
)
from .rag_pipeline import RAGPipeline, RAGPipelineError
from .patient_loader import PatientLoader, PatientLoaderError, PatientNotFoundError
from .gemini_agent import GeminiAgent, GeminiAgentError


logger = logging.getLogger(__name__)


class AssessmentEngineError(Exception):
    """Custom exception for assessment engine errors."""
    pass


class AssessmentEngine:
    """
    Clinical decision support engine for patient risk assessment.
    
    Combines patient data with NG12 guidelines through RAG pipeline
    and Gemini agent to provide evidence-based cancer risk assessments.
    """
    
    def __init__(
        self,
        rag_pipeline: RAGPipeline,
        patient_loader: PatientLoader,
        gemini_agent: GeminiAgent,
        default_top_k: int = 8
    ):
        self.rag_pipeline = rag_pipeline
        self.patient_loader = patient_loader
        self.gemini_agent = gemini_agent
        self.default_top_k = default_top_k
        
        # Inject loader into agent for Tool Use (Function Calling)
        self.gemini_agent.set_patient_loader(patient_loader)
        
        logger.info("Initialized AssessmentEngine with Tool support")
    
    async def assess_patient_risk(
        self,
        patient_id: str,
        top_k: Optional[int] = None
    ) -> AssessmentResponse:
        """
        Assess cancer risk for a patient based on their symptoms and NG12 guidelines.
        Uses Function Calling (Tools) to fetch patient data dynamically.
        """
        try:
            # 1. Fetch patient briefly just to get symptoms for RAG context building
            # The agent will later fetch the full data via Tool Use
            logger.info(f"Assessing patient risk for: {patient_id}")
            patient = await self.patient_loader.get_patient_by_id_async(patient_id)
            
            # 2. Build clinical context (Guidelines) using RAG pipeline
            k = top_k or self.default_top_k
            clinical_context = await self.rag_pipeline.build_clinical_context(
                patient_symptoms=patient.symptoms,
                patient_demographics={
                    "age": patient.age,
                    "gender": patient.gender,
                    "smoking_history": patient.smoking_history
                },
                top_k=k
            )
            
            # 3. Generate clinical assessment using Gemini with Tool Use (Function Calling)
            # We pass only the patient_id; the agent will call 'get_patient_data' tool
            assessment_response = await self.gemini_agent.generate_clinical_assessment(
                patient_id=patient_id,
                guideline_context=clinical_context["guideline_context"]
            )
            
            # 4. Parse the assessment response
            parsed_assessment = self._parse_assessment_response(assessment_response)
            
            # 5. Combine with RAG citations
            all_citations = clinical_context["citations"]
            
            # Create final assessment response
            assessment_result = AssessmentResponse(
                patient_id=patient_id,
                assessment=parsed_assessment["assessment"],
                reasoning=parsed_assessment["reasoning"],
                citations=all_citations,
                confidence_score=self._calculate_confidence_score(
                    clinical_context["num_relevant_guidelines"],
                    parsed_assessment["assessment"]
                )
            )
            
            logger.info(f"Completed assessment for {patient_id}: {parsed_assessment['assessment']}")
            return assessment_result
            
        except PatientNotFoundError:
            # Re-raise PatientNotFoundError without wrapping
            raise
        except (PatientLoaderError, RAGPipelineError, GeminiAgentError) as e:
            raise AssessmentEngineError(f"Failed to assess patient {patient_id}: {e}")
        except Exception as e:
            raise AssessmentEngineError(f"Unexpected error during assessment: {e}")
    
    def _format_patient_data(self, patient: PatientRecord) -> str:
        """
        Format patient data for clinical assessment.
        
        Args:
            patient: Patient record
            
        Returns:
            Formatted patient data string
        """
        symptoms_str = ", ".join(patient.symptoms)
        
        patient_data = f"""Patient ID: {patient.patient_id}
Age: {patient.age} years
Gender: {patient.gender}
Smoking History: {patient.smoking_history}
Presenting Symptoms: {symptoms_str}
Symptom Duration: {patient.symptom_duration_days} days

Clinical Context:
- Patient presents with {len(patient.symptoms)} symptom(s)
- Symptoms have been present for {patient.symptom_duration_days} days
- Smoking status: {patient.smoking_history}
- Demographic risk factors: {patient.age}-year-old {patient.gender.lower()}"""
        
        return patient_data
    
    def _parse_assessment_response(self, response: str) -> Dict[str, str]:
        """
        Parse the Gemini assessment response into structured components.
        
        Args:
            response: Raw response from Gemini agent
            
        Returns:
            Dictionary with parsed assessment components
        """
        # Initialize default values
        parsed = {
            "assessment": "No Action",
            "reasoning": "Unable to parse assessment response",
            "citations": ""
        }
        
        try:
            # Extract assessment classification
            assessment_match = re.search(
                r"Assessment:\s*(Urgent Referral|Urgent Investigation|No Action)",
                response,
                re.IGNORECASE
            )
            if assessment_match:
                parsed["assessment"] = assessment_match.group(1)
            
            # Extract reasoning
            reasoning_match = re.search(
                r"Reasoning:\s*(.*?)(?=Citations:|$)",
                response,
                re.DOTALL | re.IGNORECASE
            )
            if reasoning_match:
                parsed["reasoning"] = reasoning_match.group(1).strip()
            
            # Extract citations
            citations_match = re.search(
                r"Citations:\s*(.*?)$",
                response,
                re.DOTALL | re.IGNORECASE
            )
            if citations_match:
                parsed["citations"] = citations_match.group(1).strip()
            
            # Validate assessment classification
            valid_assessments = ["Urgent Referral", "Urgent Investigation", "No Action"]
            if parsed["assessment"] not in valid_assessments:
                logger.warning(f"Invalid assessment classification: {parsed['assessment']}")
                parsed["assessment"] = "No Action"
                parsed["reasoning"] = f"Assessment classification was invalid. Original response: {response[:200]}..."
            
            return parsed
            
        except Exception as e:
            logger.error(f"Failed to parse assessment response: {e}")
            parsed["reasoning"] = f"Failed to parse assessment response: {str(e)}"
            return parsed
    
    def _calculate_confidence_score(
        self,
        num_guidelines: int,
        assessment: str
    ) -> float:
        """
        Calculate confidence score based on available evidence.
        
        Args:
            num_guidelines: Number of relevant guideline chunks found
            assessment: Assessment classification
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence on number of relevant guidelines
        base_confidence = min(num_guidelines / 5.0, 1.0)  # Max confidence at 5+ guidelines
        
        # Adjust based on assessment type
        if assessment == "Urgent Referral":
            # High confidence for urgent referrals (clear red flags)
            return min(base_confidence + 0.2, 1.0)
        elif assessment == "Urgent Investigation":
            # Moderate confidence for investigations
            return base_confidence
        else:  # No Action
            # Lower confidence for no action (absence of evidence)
            return max(base_confidence - 0.1, 0.1)
    
    async def assess_multiple_patients(
        self,
        patient_ids: List[str],
        top_k: Optional[int] = None
    ) -> List[AssessmentResponse]:
        """
        Assess multiple patients in batch.
        
        Args:
            patient_ids: List of patient identifiers
            top_k: Number of guideline chunks to retrieve per patient
            
        Returns:
            List of AssessmentResponse objects
        """
        assessments = []
        
        for patient_id in patient_ids:
            try:
                assessment = await self.assess_patient_risk(patient_id, top_k)
                assessments.append(assessment)
            except AssessmentEngineError as e:
                logger.error(f"Failed to assess patient {patient_id}: {e}")
                # Create error response
                error_assessment = AssessmentResponse(
                    patient_id=patient_id,
                    assessment="No Action",
                    reasoning=f"Assessment failed: {str(e)}",
                    citations=[],
                    confidence_score=0.0
                )
                assessments.append(error_assessment)
        
        return assessments
    
    def get_assessment_statistics(self, assessments: List[AssessmentResponse]) -> Dict[str, Any]:
        """
        Generate statistics from a list of assessments.
        
        Args:
            assessments: List of assessment responses
            
        Returns:
            Dictionary with assessment statistics
        """
        if not assessments:
            return {"total": 0}
        
        # Count assessments by type
        assessment_counts = {
            "Urgent Referral": 0,
            "Urgent Investigation": 0,
            "No Action": 0
        }
        
        total_confidence = 0.0
        total_citations = 0
        
        for assessment in assessments:
            assessment_counts[assessment.assessment] += 1
            if assessment.confidence_score:
                total_confidence += assessment.confidence_score
            total_citations += len(assessment.citations)
        
        return {
            "total": len(assessments),
            "urgent_referrals": assessment_counts["Urgent Referral"],
            "urgent_investigations": assessment_counts["Urgent Investigation"],
            "no_actions": assessment_counts["No Action"],
            "average_confidence": total_confidence / len(assessments) if assessments else 0.0,
            "average_citations": total_citations / len(assessments) if assessments else 0.0,
            "referral_rate": assessment_counts["Urgent Referral"] / len(assessments) * 100,
            "investigation_rate": assessment_counts["Urgent Investigation"] / len(assessments) * 100
        }
    
    async def validate_assessment_quality(
        self,
        assessment: AssessmentResponse
    ) -> Dict[str, Any]:
        """
        Validate the quality of an assessment response.
        
        Args:
            assessment: Assessment response to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            "valid": True,
            "issues": [],
            "score": 1.0
        }
        
        # Check assessment classification
        valid_assessments = ["Urgent Referral", "Urgent Investigation", "No Action"]
        if assessment.assessment not in valid_assessments:
            validation["valid"] = False
            validation["issues"].append("Invalid assessment classification")
            validation["score"] -= 0.3
        
        # Check reasoning quality
        if not assessment.reasoning or len(assessment.reasoning.strip()) < 20:
            validation["issues"].append("Insufficient reasoning provided")
            validation["score"] -= 0.2
        
        # Check citations
        if not assessment.citations:
            validation["issues"].append("No citations provided")
            validation["score"] -= 0.3
        else:
            # Validate citation quality
            for citation in assessment.citations:
                if not citation.page or not citation.excerpt:
                    validation["issues"].append("Incomplete citation information")
                    validation["score"] -= 0.1
                    break
        
        # Check confidence score
        if assessment.confidence_score is None or assessment.confidence_score < 0 or assessment.confidence_score > 1:
            validation["issues"].append("Invalid confidence score")
            validation["score"] -= 0.1
        
        validation["score"] = max(validation["score"], 0.0)
        
        return validation
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of the assessment engine.
        
        Returns:
            Dictionary with health status
        """
        health_status = {
            "engine_healthy": True,
            "components": {}
        }
        
        try:
            # Check RAG pipeline
            rag_health = await self.rag_pipeline.health_check()
            health_status["components"]["rag_pipeline"] = rag_health
            
            # Check patient loader
            patient_health = await self.patient_loader.health_check()
            health_status["components"]["patient_loader"] = patient_health
            
            # Check Gemini agent
            gemini_health = await self.gemini_agent.health_check()
            health_status["components"]["gemini_agent"] = {
                "healthy": gemini_health,
                "model_info": self.gemini_agent.get_model_info()
            }
            
            # Overall health
            health_status["engine_healthy"] = (
                rag_health.get("pipeline_healthy", False) and
                patient_health and
                gemini_health
            )
            
            return health_status
            
        except Exception as e:
            health_status["engine_healthy"] = False
            health_status["error"] = str(e)
            return health_status
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the assessment engine configuration.
        
        Returns:
            Dictionary with engine statistics
        """
        return {
            "default_top_k": self.default_top_k,
            "rag_pipeline_stats": self.rag_pipeline.get_pipeline_stats(),
            "gemini_model_info": self.gemini_agent.get_model_info(),
            "patient_loader_stats": self.patient_loader.get_loader_stats()
        }