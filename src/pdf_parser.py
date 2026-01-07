"""
PDF parser for the NG12 Cancer Risk Assessor.
Downloads and parses the NICE NG12 Cancer Guidelines PDF with metadata preservation.
"""
import logging
import re
import requests
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import PyPDF2
from .models import TextChunk


logger = logging.getLogger(__name__)


class PDFParserError(Exception):
    """Custom exception for PDF parser errors."""
    pass


class PDFDownloadError(PDFParserError):
    """Exception raised when PDF download fails."""
    pass


class PDFParsingError(PDFParserError):
    """Exception raised when PDF parsing fails."""
    pass


class PDFParser:
    """
    Downloads and parses the NICE NG12 Cancer Guidelines PDF.
    
    Extracts text with page metadata and implements semantic chunking
    strategy that preserves section structure for optimal RAG performance.
    """
    
    # Official NICE NG12 PDF URL (may need updating)
    NG12_PDF_URL = "https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf-1837268071621"
    
    # Alternative URLs to try
    ALTERNATIVE_URLS = [
        "https://www.nice.org.uk/guidance/ng12/resources/suspected-cancer-recognition-and-referral-pdf",
        "https://www.nice.org.uk/guidance/ng12/chapter/recommendations"
    ]
    
    def __init__(self, pdf_path: Optional[str] = None, download_dir: str = "data"):
        """
        Initialize the PDFParser.
        
        Args:
            pdf_path: Path to existing PDF file (optional)
            download_dir: Directory to download PDF if not provided
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        if pdf_path:
            self.pdf_path = Path(pdf_path)
        else:
            self.pdf_path = self.download_dir / "ng12_guidelines.pdf"
            
        self._text_chunks: Optional[List[TextChunk]] = None
    
    def download_ng12_pdf(self, force_download: bool = False, use_mock_on_failure: bool = True) -> Path:
        """
        Download the NG12 PDF from the official NICE URL.
        
        Args:
            force_download: If True, download even if file exists
            use_mock_on_failure: If True, create mock content if download fails
            
        Returns:
            Path to the downloaded PDF file or mock content indicator
            
        Raises:
            PDFDownloadError: If download fails and use_mock_on_failure is False
        """
        if self.pdf_path.exists() and not force_download:
            logger.info(f"PDF already exists at {self.pdf_path}")
            return self.pdf_path
            
        # Try main URL first, then alternatives
        urls_to_try = [self.NG12_PDF_URL] + self.ALTERNATIVE_URLS
        
        for url in urls_to_try:
            try:
                logger.info(f"Attempting to download NG12 PDF from {url}")
                
                # Download with proper headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Verify it's a PDF file
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' in content_type or response.content.startswith(b'%PDF'):
                    # Save the PDF
                    with open(self.pdf_path, 'wb') as f:
                        f.write(response.content)
                        
                    logger.info(f"Successfully downloaded NG12 PDF to {self.pdf_path} ({len(response.content)} bytes)")
                    return self.pdf_path
                else:
                    logger.warning(f"URL {url} did not return a PDF file")
                    continue
                    
            except requests.RequestException as e:
                logger.warning(f"Failed to download from {url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error downloading from {url}: {e}")
                continue
        
        # If all downloads failed
        if use_mock_on_failure:
            logger.info("All download attempts failed, using mock NG12 content for development")
            # Create a marker file to indicate we're using mock content
            mock_marker = self.download_dir / "using_mock_ng12_content.txt"
            with open(mock_marker, 'w') as f:
                f.write("Using mock NG12 content because PDF download failed\n")
            return mock_marker
        else:
            raise PDFDownloadError("Failed to download NG12 PDF from all attempted URLs")
    
    def extract_text_with_metadata(self) -> List[TextChunk]:
        """
        Extract text from PDF with page metadata and semantic chunking.
        
        Returns:
            List of TextChunk objects with content and metadata
            
        Raises:
            PDFParsingError: If PDF parsing fails
        """
        if self._text_chunks is not None:
            return self._text_chunks
        
        # Check if we're using mock content
        mock_marker = self.download_dir / "using_mock_ng12_content.txt"
        if mock_marker.exists():
            logger.info("Using mock NG12 content for development")
            return self.create_mock_ng12_content()
            
        if not self.pdf_path.exists():
            raise PDFParsingError(f"PDF file not found: {self.pdf_path}")
            
        try:
            logger.info(f"Extracting text from PDF: {self.pdf_path}")
            
            chunks = []
            
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                logger.info(f"Processing {total_pages} pages")
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        # Extract text from page
                        text = page.extract_text()
                        
                        if text.strip():  # Only process pages with text
                            # Create chunks for this page
                            page_chunks = self._chunk_text(text, page_num)
                            chunks.extend(page_chunks)
                            
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num}: {e}")
                        continue
            
            logger.info(f"Successfully extracted {len(chunks)} text chunks from {total_pages} pages")
            self._text_chunks = chunks
            return chunks
            
        except Exception as e:
            raise PDFParsingError(f"Failed to parse PDF: {e}")
    
    def _chunk_text(self, text: str, page_num: int) -> List[TextChunk]:
        """
        Create semantic chunks from page text preserving section structure.
        
        Args:
            text: Raw text from PDF page
            page_num: Page number for metadata
            
        Returns:
            List of TextChunk objects for the page
        """
        chunks = []
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        if not text.strip():
            return chunks
            
        # Extract section headers for context
        section_title = self._extract_section_title(text)
        
        # Split text into semantic chunks
        # Target chunk size: 200-400 tokens (roughly 800-1600 characters)
        target_chunk_size = 1200
        overlap_size = 200
        
        # Split by paragraphs first to maintain semantic boundaries
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = ""
        chunk_start = 0
        chunk_count = 0
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed target size, create a chunk
            if len(current_chunk) + len(paragraph) > target_chunk_size and current_chunk:
                chunk_count += 1
                chunk_id = f"ng12_{page_num:04d}_{chunk_count:02d}"
                
                chunk = TextChunk(
                    chunk_id=chunk_id,
                    content=current_chunk.strip(),
                    page_number=page_num,
                    section_title=section_title,
                    start_char=chunk_start,
                    end_char=chunk_start + len(current_chunk)
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-overlap_size:] if len(current_chunk) > overlap_size else current_chunk
                current_chunk = overlap_text + "\n" + paragraph
                chunk_start += len(current_chunk) - len(overlap_text) - len(paragraph) - 1
            else:
                if current_chunk:
                    current_chunk += "\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add final chunk if there's remaining content
        if current_chunk.strip():
            chunk_count += 1
            chunk_id = f"ng12_{page_num:04d}_{chunk_count:02d}"
            
            chunk = TextChunk(
                chunk_id=chunk_id,
                content=current_chunk.strip(),
                page_number=page_num,
                section_title=section_title,
                start_char=chunk_start,
                end_char=chunk_start + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page headers/footers (common patterns)
        text = re.sub(r'NICE guideline.*?\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        
        # Fix common PDF extraction issues
        text = text.replace('ﬁ', 'fi')  # Fix ligatures
        text = text.replace('ﬂ', 'fl')
        text = text.replace('\u2019', "'")    # Fix right single quote
        text = text.replace('\u201c', '"')    # Fix left double quote
        text = text.replace('\u201d', '"')    # Fix right double quote
        
        return text.strip()
    
    def _extract_section_title(self, text: str) -> str:
        """
        Extract section title from page text.
        
        Args:
            text: Page text
            
        Returns:
            Section title or default
        """
        # Look for common section patterns in NG12
        patterns = [
            r'^(\d+\.?\d*\s+[A-Z][^.\n]{10,60})',  # Numbered sections
            r'^([A-Z][A-Z\s]{5,40})\n',            # All caps headers
            r'(Recommendation \d+\.?\d*)',          # Recommendations
            r'(Clinical question \d+\.?\d*)',       # Clinical questions
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Fallback: use first line if it looks like a title
        first_line = text.split('\n')[0].strip()
        if len(first_line) < 100 and first_line:
            return first_line
            
        return "NG12 Guidelines"
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs while preserving structure.
        
        Args:
            text: Input text
            
        Returns:
            List of paragraph strings
        """
        # Split by double newlines or bullet points
        paragraphs = re.split(r'\n\s*\n|\n\s*[•·▪▫]\s*', text)
        
        # Filter out very short paragraphs (likely artifacts)
        paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 20]
        
        return paragraphs
    
    def create_mock_ng12_content(self) -> List[TextChunk]:
        """
        Create mock NG12 content for development and testing.
        
        Returns:
            List of TextChunk objects with sample NG12-like content
        """
        mock_content = """
        1. Introduction
        
        This guideline covers identifying children, young people and adults with symptoms 
        that could be caused by cancer. It outlines appropriate investigations in primary 
        care, and selection of people to refer for a specialist opinion.
        
        1.1 Who is it for?
        
        This guideline is for healthcare professionals in primary care, including GPs, 
        practice nurses, and other healthcare professionals who may encounter people 
        with symptoms that could indicate cancer.
        
        2. Recommendations
        
        2.1 General principles for cancer referral
        
        Healthcare professionals should be aware that cancer can present with a wide 
        variety of symptoms and signs. Some symptoms are more predictive of cancer 
        than others, but even symptoms with a low predictive value can be associated 
        with cancer.
        
        2.2 Lung cancer referral criteria
        
        Consider an urgent chest X-ray (to be performed within 2 weeks) to assess 
        for lung cancer in people aged 40 and over if they have 2 or more of the 
        following unexplained symptoms, or if they have ever smoked and have 1 or 
        more of the following unexplained symptoms:
        
        • cough
        • fatigue
        • shortness of breath
        • chest pain
        • weight loss
        • appetite loss
        
        Refer people using a suspected cancer pathway referral (for an appointment 
        within 2 weeks) for lung cancer if they have:
        
        • chest X-ray findings that suggest lung cancer or
        • aged 40 and over with unexplained haemoptysis
        
        2.3 Breast cancer referral criteria
        
        Refer people using a suspected cancer pathway referral (for an appointment 
        within 2 weeks) for breast cancer if they are:
        
        • aged 30 and over and have an unexplained breast lump with or without pain or
        • aged 50 and over with any of the following symptoms in one nipple only:
          - nipple discharge
          - nipple retraction
          - other changes of concern
        
        2.4 Colorectal cancer referral criteria
        
        Refer adults using a suspected cancer pathway referral (for an appointment 
        within 2 weeks) for colorectal cancer if:
        
        • they are aged 40 and over with unexplained weight loss and abdominal pain or
        • they are aged 50 and over with unexplained rectal bleeding or
        • they are aged 60 and over with iron-deficiency anaemia or changes in their 
          bowel habit
        
        Consider a suspected cancer pathway referral (for an appointment within 2 weeks) 
        for colorectal cancer in adults with a rectal or abdominal mass.
        
        2.5 Upper gastrointestinal cancer referral criteria
        
        Consider an urgent direct access upper gastrointestinal endoscopy (to be 
        performed within 2 weeks) to assess for oesophageal cancer in people:
        
        • aged 55 and over with weight loss and any of the following:
          - upper abdominal pain
          - reflux
          - dysphagia
        
        Refer people using a suspected cancer pathway referral (for an appointment 
        within 2 weeks) for oesophageal cancer if they have dysphagia or
        aged 55 and over with weight loss and upper abdominal pain or reflux.
        
        3. Implementation considerations
        
        3.1 Training and education
        
        Healthcare professionals should receive appropriate training on cancer 
        recognition and referral pathways to ensure consistent implementation 
        of these guidelines.
        
        3.2 Patient communication
        
        When referring patients for suspected cancer investigations, healthcare 
        professionals should:
        
        • explain the reason for referral clearly
        • provide appropriate information about what to expect
        • offer support and reassurance while maintaining clinical urgency
        
        4. Monitoring and audit
        
        Healthcare organizations should monitor:
        
        • referral rates for suspected cancer
        • time to diagnosis
        • patient outcomes
        • adherence to guideline recommendations
        """
        
        # Create chunks from mock content
        chunks = self._chunk_text(mock_content, 1)
        
        # Add some additional pages of content
        additional_pages = [
            "5. Specific cancer types\n\n5.1 Skin cancer\n\nRefer people using a suspected cancer pathway referral for skin cancer if they have a suspicious pigmented skin lesion with a weighted 7-point checklist score of 3 or above.",
            "6. Children and young people\n\n6.1 General considerations\n\nBe aware that cancer is rare in children and young people, but healthcare professionals should still be alert to signs and symptoms that may indicate cancer.",
            "7. Follow-up and monitoring\n\n7.1 Post-referral care\n\nAfter referring a patient for suspected cancer, primary care should maintain appropriate follow-up and support."
        ]
        
        for page_num, content in enumerate(additional_pages, 2):
            page_chunks = self._chunk_text(content, page_num)
            chunks.extend(page_chunks)
        
        logger.info(f"Created {len(chunks)} mock NG12 content chunks")
        self._text_chunks = chunks
        return chunks
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[TextChunk]:
        """
        Retrieve a specific chunk by ID.
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            TextChunk object or None if not found
        """
        if self._text_chunks is None:
            self.extract_text_with_metadata()
            
        for chunk in self._text_chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
                
        return None
    
    def get_chunks_by_page(self, page_number: int) -> List[TextChunk]:
        """
        Get all chunks from a specific page.
        
        Args:
            page_number: Page number
            
        Returns:
            List of TextChunk objects from the page
        """
        if self._text_chunks is None:
            self.extract_text_with_metadata()
            
        return [chunk for chunk in self._text_chunks if chunk.page_number == page_number]
    
    def save_chunks_to_file(self, output_path: str) -> None:
        """
        Save extracted chunks to a JSON file for debugging.
        
        Args:
            output_path: Path to save the chunks
        """
        import json
        
        if self._text_chunks is None:
            self.extract_text_with_metadata()
            
        chunks_data = [
            {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char
            }
            for chunk in self._text_chunks
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved {len(chunks_data)} chunks to {output_path}")