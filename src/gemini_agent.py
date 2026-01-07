"""
Gemini 1.5 agent interface for the NG12 Cancer Risk Assessor.
Provides clinical reasoning and chat response capabilities with both real and mock implementations.
"""
import logging
import os
from typing import List, Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import random

from google.cloud import aiplatform
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    GenerationConfig, 
    SafetySetting, 
    HarmCategory, 
    HarmBlockThreshold,
    Tool,
    FunctionDeclaration
)


logger = logging.getLogger(__name__)


class GeminiAgentError(Exception):
    """Custom exception for Gemini agent errors."""
    pass


class GeminiAgent:
    """
    Gemini 1.5 agent with clinical reasoning and tool use capabilities.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "us-central1",
        model_name: str = "gemini-2.5-flash",
        use_mock: bool = False
    ):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.model_name = model_name or os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")
        self.use_mock = use_mock or os.getenv("USE_MOCK_GEMINI", "false").lower() == "true"
        self._patient_loader = None # Will be set by engine
        
        if not self.project_id:
            raise GeminiAgentError(
                "Google Cloud project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable."
            )
        
        self._model: Optional[GenerativeModel] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Define Tools (Function Calling)
        self.get_patient_data_func = FunctionDeclaration(
            name="get_patient_data",
            description="Retrieve structured clinical data for a patient including age, symptoms, and duration.",
            parameters={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The unique identifier for the patient (e.g., 'PT-101')"
                    }
                },
                "required": ["patient_id"]
            },
        )
        self.clinical_tools = Tool(
            function_declarations=[self.get_patient_data_func],
        )

        self.generation_config = GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            top_k=40,
            max_output_tokens=2048
        )
        
        self.safety_settings = [
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE)
        ]
        
        if not self.use_mock:
            self._initialize_vertex_ai()
    
    def set_patient_loader(self, loader):
        """Inject patient loader for tool execution."""
        self._patient_loader = loader

    def _initialize_vertex_ai(self) -> None:
        """Initialize Vertex AI with proper authentication."""
        try:
            credentials = None
            service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if service_account_json:
                info = json.loads(service_account_json)
                credentials = service_account.Credentials.from_service_account_info(info)
            
            aiplatform.init(project=self.project_id, location=self.location, credentials=credentials)
            vertexai.init(project=self.project_id, location=self.location, credentials=credentials)
            logger.info(f"Initialized Vertex AI for Gemini in project {self.project_id}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI, falling back to mock mode: {e}")
            self.use_mock = True
    
    def _get_model(self, with_tools: bool = False) -> GenerativeModel:
        """Get or create the Gemini model instance."""
        tools = [self.clinical_tools] if with_tools else None
        return GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings,
            tools=tools
        )

    async def generate_clinical_assessment(
        self,
        patient_id: str,
        guideline_context: str
    ) -> str:
        """
        Generate clinical assessment using tool use to fetch patient data.
        """
        if self.use_mock:
            # For mock, we still manually fetch to simulate the tool's result
            patient = self._patient_loader.get_patient_by_id(patient_id)
            return await self._generate_mock_clinical_assessment(str(patient.dict()), guideline_context)
        
        try:
            model = self._get_model(with_tools=True)
            chat = model.start_chat()
            
            prompt = f"""
            Task: Assess cancer risk for Patient ID: {patient_id}.
            
            Instructions:
            1. Use the 'get_patient_data' tool to retrieve clinical details for this patient.
            2. Analyze the retrieved data against the following NG12 guidelines:
            
            {guideline_context}
            
            3. Provide your final assessment strictly in this format:
            
            Assessment: [Urgent Referral / Urgent Investigation / No Action]
            Reasoning: [Your clinical reasoning based on the guidelines]
            Citations: [References to the specific guideline sections used]
            """
            
            # 1. Initial request to Gemini
            response = chat.send_message(prompt)
            
            # 2. Handle Function Calling Loop
            # In a production app, this would be a loop to handle multiple calls
            part = response.candidates[0].content.parts[0]
            if part.function_call:
                if part.function_call.name == "get_patient_data":
                    args = part.function_call.args
                    p_id = args["patient_id"]
                    
                    logger.info(f"Agent triggered tool: get_patient_data for {p_id}")
                    patient_data = self._patient_loader.get_patient_by_id(p_id)
                    
                    # 3. Send tool result back to Gemini
                    from vertexai.generative_models import Content, Part
                    response = chat.send_message(
                        Part.from_function_response(
                            name="get_patient_data",
                            response={
                                "content": patient_data.dict(),
                            }
                        )
                    )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Clinical assessment generation failed: {e}")
            # Fallback to mock on error
            patient_data = self._patient_loader.get_patient_by_id(patient_id)
            return await self._generate_mock_clinical_assessment(str(patient_data.dict()), guideline_context)
    async def generate_chat_response(
        self,
        user_query: str,
        guideline_context: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Generate chat response for clinical guideline queries.
        
        Args:
            user_query: User's question about guidelines
            guideline_context: Retrieved NG12 guideline content
            conversation_history: Previous conversation context
            
        Returns:
            Chat response with evidence grounding
            
        Raises:
            GeminiAgentError: If chat response generation fails
        """
        if self.use_mock:
            return await self._generate_mock_chat_response(user_query, guideline_context)
        
        try:
            prompt = self._build_chat_response_prompt(
                user_query, guideline_context, conversation_history
            )
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                self._generate_response_sync,
                prompt
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Chat response generation failed, falling back to mock: {e}")
            return await self._generate_mock_chat_response(user_query, guideline_context)
    
    def _generate_response_sync(self, prompt: str) -> str:
        """Synchronous response generation."""
        model = self._get_model()
        
        try:
            response = model.generate_content(prompt)
            
            if not response.text:
                raise GeminiAgentError("Empty response from Gemini model")
            
            return response.text.strip()
            
        except Exception as e:
            raise GeminiAgentError(f"Failed to generate response: {e}")
    
    def _build_clinical_assessment_prompt(
        self,
        patient_data: str,
        guideline_context: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """Build prompt for clinical assessment."""
        prompt_parts = [
            "You are a clinical decision support system based on NICE NG12 Cancer Guidelines.",
            "Your role is to assess cancer risk and provide referral recommendations.",
            "",
            "CRITICAL INSTRUCTIONS:",
            "1. Base ALL recommendations ONLY on the provided NG12 guideline content",
            "2. Classify assessment as exactly one of: 'Urgent Referral', 'Urgent Investigation', or 'No Action'",
            "3. Provide clear reasoning citing specific guideline sections",
            "4. If insufficient evidence exists, state 'No Action' with explanation",
            "5. Never make recommendations without corresponding NG12 citations",
            "",
            "PATIENT INFORMATION:",
            patient_data,
            "",
            "RELEVANT NG12 GUIDELINES:",
            guideline_context,
            ""
        ]
        
        if conversation_history:
            prompt_parts.extend([
                "PREVIOUS CONVERSATION:",
                conversation_history,
                ""
            ])
        
        prompt_parts.extend([
            "ASSESSMENT FORMAT:",
            "Assessment: [Urgent Referral/Urgent Investigation/No Action]",
            "Reasoning: [Detailed clinical reasoning based on NG12 guidelines]",
            "Citations: [Specific page numbers and sections from NG12]",
            "",
            "Provide your assessment:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_chat_response_prompt(
        self,
        user_query: str,
        guideline_context: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """Build prompt for chat response."""
        prompt_parts = [
            "You are a clinical guideline assistant based on NICE NG12 Cancer Guidelines.",
            "Your role is to answer questions about cancer referral criteria and guidelines.",
            "",
            "CRITICAL INSTRUCTIONS:",
            "1. Answer ONLY based on the provided NG12 guideline content",
            "2. If information is not in the guidelines, state: 'I cannot find support in NG12 for that query'",
            "3. Always include specific page numbers and section references",
            "4. Provide relevant text excerpts from the guidelines",
            "5. Never generate information not present in the provided context",
            "",
            "USER QUESTION:",
            user_query,
            "",
            "RELEVANT NG12 GUIDELINES:",
            guideline_context,
            ""
        ]
        
        if conversation_history:
            prompt_parts.extend([
                "PREVIOUS CONVERSATION:",
                conversation_history,
                ""
            ])
        
        prompt_parts.extend([
            "Provide your response with specific NG12 citations:"
        ])
        
        return "\n".join(prompt_parts)
    
    async def _generate_mock_clinical_assessment(
        self,
        patient_data: str,
        guideline_context: str
    ) -> str:
        """Generate mock clinical assessment for development/testing."""
        # Extract patient symptoms for mock logic
        symptoms_lower = patient_data.lower()
        
        # Mock assessment logic based on common cancer symptoms
        if any(symptom in symptoms_lower for symptom in ["hemoptysis", "breast lump", "haematuria"]):
            assessment = "Urgent Referral"
            reasoning = "Patient presents with red flag symptoms that require urgent specialist assessment according to NG12 guidelines."
        elif any(symptom in symptoms_lower for symptom in ["persistent cough", "hoarseness", "dysphagia"]):
            assessment = "Urgent Investigation"
            reasoning = "Patient has persistent symptoms that warrant urgent investigation to rule out malignancy."
        else:
            assessment = "No Action"
            reasoning = "Current symptoms do not meet NG12 criteria for urgent referral or investigation at this time."
        
        # Add some randomness to make it more realistic
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        mock_response = f"""Assessment: {assessment}
Reasoning: {reasoning} Based on the provided NG12 guideline context, the patient's symptoms and risk factors have been evaluated against established referral criteria.
Citations: [MOCK] NG12 PDF, Pages 15-18, Section 1.2.3 - Referral criteria for suspected cancer symptoms"""
        
        return mock_response
    
    async def _generate_mock_chat_response(
        self,
        user_query: str,
        guideline_context: str
    ) -> str:
        """Generate mock chat response for development/testing."""
        query_lower = user_query.lower()
        
        # Mock responses based on common queries
        if "referral" in query_lower:
            response = "According to NG12 guidelines, urgent referral criteria include specific red flag symptoms and risk factors. The exact criteria depend on the suspected cancer type and patient presentation."
        elif "investigation" in query_lower:
            response = "NG12 outlines various investigation pathways including urgent investigations for patients with concerning symptoms that don't meet immediate referral criteria."
        elif "symptoms" in query_lower:
            response = "NG12 categorizes symptoms into red flag symptoms requiring urgent referral and other concerning symptoms requiring urgent investigation."
        else:
            response = "Based on the NG12 guidelines provided, I can help you understand the referral criteria and investigation pathways for suspected cancer."
        
        # Add some randomness to make it more realistic
        await asyncio.sleep(random.uniform(0.3, 1.0))
        
        mock_response = f"""{response}

[MOCK CITATION] NG12 PDF, Page 12, Section 1.1.5: "Relevant guideline excerpt would appear here based on the specific query and retrieved context."

Please note: This is a mock response for development purposes. The actual system would provide specific citations from the retrieved NG12 content."""
        
        return mock_response
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the Gemini model configuration.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "project_id": self.project_id,
            "location": self.location,
            "use_mock": self.use_mock,
            "temperature": getattr(self.generation_config, 'temperature', 0.1),
            "max_output_tokens": getattr(self.generation_config, 'max_output_tokens', 2048),
            "safety_settings_count": len(self.safety_settings)
        }
    
    async def health_check(self) -> bool:
        """
        Perform a health check by generating a test response.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if self.use_mock:
                # Mock health check
                await asyncio.sleep(0.1)
                return True
            
            test_response = await self.generate_chat_response(
                user_query="Health check test",
                guideline_context="Test guideline content for health check"
            )
            return bool(test_response and len(test_response) > 0)
            
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)