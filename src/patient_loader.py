"""
Patient data loader for the NG12 Cancer Risk Assessor.
Handles loading and validation of patient data from JSON files.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import PatientRecord


logger = logging.getLogger(__name__)


class PatientLoaderError(Exception):
    """Custom exception for patient loader errors."""
    pass


class PatientNotFoundError(PatientLoaderError):
    """Exception raised when a patient is not found."""
    pass


class PatientDataValidationError(PatientLoaderError):
    """Exception raised when patient data validation fails."""
    pass


class PatientLoader:
    """
    Loads and validates patient data from JSON files.
    
    Provides methods to retrieve patient records by ID with proper error handling
    and validation according to the PatientRecord model.
    """
    
    def __init__(self, data_file_path: str = "data/patients.json"):
        """
        Initialize the PatientLoader.
        
        Args:
            data_file_path: Path to the JSON file containing patient data
        """
        self.data_file_path = Path(data_file_path)
        self._patients_cache: Optional[Dict[str, PatientRecord]] = None
        
    def _load_patients_data(self) -> Dict[str, PatientRecord]:
        """
        Load and validate patient data from the JSON file.
        
        Returns:
            Dictionary mapping patient IDs to PatientRecord objects
            
        Raises:
            PatientLoaderError: If file cannot be read or data is invalid
            PatientDataValidationError: If patient data doesn't match schema
        """
        try:
            if not self.data_file_path.exists():
                raise PatientLoaderError(f"Patient data file not found: {self.data_file_path}")
                
            with open(self.data_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if 'patients' not in data:
                raise PatientLoaderError("Invalid JSON structure: missing 'patients' key")
                
            patients_dict = {}
            for patient_data in data['patients']:
                try:
                    # Validate patient data using Pydantic model
                    patient = PatientRecord(**patient_data)
                    patients_dict[patient.patient_id] = patient
                except Exception as e:
                    raise PatientDataValidationError(
                        f"Invalid patient data for ID {patient_data.get('patient_id', 'unknown')}: {e}"
                    )
                    
            logger.info(f"Successfully loaded {len(patients_dict)} patients from {self.data_file_path}")
            return patients_dict
            
        except json.JSONDecodeError as e:
            raise PatientLoaderError(f"Invalid JSON in patient data file: {e}")
        except Exception as e:
            if isinstance(e, PatientLoaderError):
                raise
            raise PatientLoaderError(f"Unexpected error loading patient data: {e}")
    
    def get_patient_by_id(self, patient_id: str) -> PatientRecord:
        """
        Retrieve a patient record by ID.
        
        Args:
            patient_id: The unique identifier for the patient
            
        Returns:
            PatientRecord object containing the patient's data
            
        Raises:
            PatientNotFoundError: If the patient ID is not found
            PatientLoaderError: If there's an error loading the data
        """
        if not patient_id:
            raise PatientNotFoundError("Patient ID cannot be empty")
            
        # Load patients data if not cached
        if self._patients_cache is None:
            self._patients_cache = self._load_patients_data()
            
        if patient_id not in self._patients_cache:
            raise PatientNotFoundError(f"Patient with ID '{patient_id}' not found")
            
        return self._patients_cache[patient_id]
    
    async def get_patient_by_id_async(self, patient_id: str) -> PatientRecord:
        """
        Async version of get_patient_by_id for compatibility with async workflows.
        
        Args:
            patient_id: The unique identifier for the patient
            
        Returns:
            PatientRecord object containing the patient's data
        """
        return self.get_patient_by_id(patient_id)
    
    def get_all_patients(self) -> List[PatientRecord]:
        """
        Retrieve all patient records.
        
        Returns:
            List of all PatientRecord objects
            
        Raises:
            PatientLoaderError: If there's an error loading the data
        """
        if self._patients_cache is None:
            self._patients_cache = self._load_patients_data()
            
        return list(self._patients_cache.values())
    
    def get_patient_ids(self) -> List[str]:
        """
        Get all available patient IDs.
        
        Returns:
            List of patient ID strings
            
        Raises:
            PatientLoaderError: If there's an error loading the data
        """
        if self._patients_cache is None:
            self._patients_cache = self._load_patients_data()
            
        return list(self._patients_cache.keys())
    
    def reload_data(self) -> None:
        """
        Force reload of patient data from file.
        
        Clears the cache and reloads data on next access.
        """
        self._patients_cache = None
        logger.info("Patient data cache cleared, will reload on next access")
    
    def validate_patient_data(self, patient_data: dict) -> PatientRecord:
        """
        Validate patient data against the PatientRecord schema.
        
        Args:
            patient_data: Dictionary containing patient data
            
        Returns:
            Validated PatientRecord object
            
        Raises:
            PatientDataValidationError: If validation fails
        """
        try:
            return PatientRecord(**patient_data)
        except Exception as e:
            raise PatientDataValidationError(f"Patient data validation failed: {e}")
    
    async def health_check(self) -> bool:
        """
        Perform a health check by attempting to load patient data.
        
        Returns:
            True if patient data can be loaded successfully, False otherwise
        """
        try:
            patients = self._load_patients_data()
            return len(patients) > 0
        except Exception as e:
            logger.error(f"Patient loader health check failed: {e}")
            return False
    
    def get_loader_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the patient loader.
        
        Returns:
            Dictionary with loader statistics
        """
        try:
            if self._patients_cache is None:
                self._patients_cache = self._load_patients_data()
            
            return {
                "total_patients": len(self._patients_cache),
                "data_file_path": str(self.data_file_path),
                "cache_loaded": self._patients_cache is not None,
                "patient_ids": list(self._patients_cache.keys()) if self._patients_cache else []
            }
        except Exception as e:
            return {
                "total_patients": 0,
                "data_file_path": str(self.data_file_path),
                "cache_loaded": False,
                "error": str(e)
            }