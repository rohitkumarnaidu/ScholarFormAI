# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Input Conversion Module - Handles multi-format document conversion.
"""

import os
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class ConversionError(Exception):
    """Raised when conversion fails."""
    pass

class InputConverter:
    """
    Converts various input formats to a standardized DOCX format
    for pipeline processing.
    """
    
    SUPPORTED_EXTENSIONS = {
        '.docx': 'pass',
        '.doc':  'libreoffice',   # A-FIX-1: was missing — caused ConversionError on .doc uploads
        '.md':   'pandoc',
        '.html': 'pandoc',
        '.txt':  'pandoc',
        '.tex':  'pandoc',        # LaTeX support via Pandoc
        '.pdf':  'libreoffice',
        '.odt':  'libreoffice',   # A-FIX-25: OpenDocument support
        '.rtf':  'libreoffice',   # A-FIX-25: Rich Text Format support
    }
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
    def convert_to_docx(self, input_path: str, job_id: str, enable_ocr: bool = True) -> str:
        """
        Convert input file to DOCX.
        
        Args:
            input_path: Path to source file
            job_id: Unique job identifier for temp isolation
            enable_ocr: Whether to attempt OCR for scanned PDFs
            
        Returns:
            Path to the resulting .docx file
            
        Raises:
            ConversionError: If format unsupported or tool missing/failed
        """
        input_path = os.path.abspath(input_path)
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        _, ext = os.path.splitext(input_path)
        ext = ext.lower()
        
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ConversionError(f"Unsupported file format: {ext}")
            
        strategy = self.SUPPORTED_EXTENSIONS[ext]
        
        # Prepare Output Path
        job_dir = os.path.join(self.temp_dir, str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        output_path = os.path.join(job_dir, "input.docx")
        
        # Strategy Execution
        if strategy == 'pass':
            # Just copy to standardize location
            shutil.copy2(input_path, output_path)
            return output_path
            
        elif strategy == 'pandoc':
            self._run_pandoc(input_path, output_path)
            return output_path
            
        elif strategy == 'libreoffice':
            if ext == '.pdf':
                return self._handle_pdf(input_path, job_dir, job_id, enable_ocr)

            self._run_libreoffice(input_path, job_dir)
            # LibreOffice output name might need handling
            # It saves as [filename].docx in outdir.
            # We need to rename it to input.docx if needed, 
            # or just return the generated name.
            
            # Predict LO output name
            input_name = Path(input_path).stem
            lo_output = os.path.join(job_dir, f"{input_name}.docx")
            
            if os.path.exists(lo_output):
                # Rename to standard input.docx
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(lo_output, output_path)
                return output_path
            else:
                raise ConversionError("LibreOffice conversion failed to produce output file")
        
        return output_path

    def _handle_pdf(self, input_path: str, output_dir: str, job_id: str, enable_ocr: bool) -> str:
        """
        Handle PDF conversion. 
        Auto-detects scanned PDFs and applies OCR if needed.
        """
        from app.pipeline.ocr.pdf_ocr import PdfOCR, OCRError
        from app.services.enhancement_manager import enhancement_manager
        
        output_path = os.path.join(output_dir, "input.docx")
        profile = enhancement_manager.profile
        if not (profile.enabled and profile.ocr_enabled):
            enable_ocr = False
            logger.info(
                "Job %s: OCR enhancement disabled by capability profile. Using LibreOffice fallback path.",
                job_id,
            )
        ocr_backends = enhancement_manager.get_ocr_backends()
        
        supported_ocr_backends = [backend for backend in ocr_backends if backend in {"tesseract", "paddle"}]

        if enable_ocr and supported_ocr_backends:
            # Check if scanned
            ocr = PdfOCR()
            is_scanned = ocr.is_scanned(input_path)

            if is_scanned:
                try:
                    logger.info("Job %s: PDF detected as scanned. Attempting OCR...", job_id)
                    ocr.convert_to_docx(input_path, output_path, backends=supported_ocr_backends)
                    logger.info("Job %s: OCR conversion successful.", job_id)
                    return output_path
                except OCRError as exc:
                    logger.warning("Job %s: OCR failed (%s). Falling back to LibreOffice.", job_id, exc)
                except Exception as exc:
                    logger.warning("Job %s: Unexpected OCR error (%s). Falling back.", job_id, exc)
        elif enable_ocr:
            logger.info(
                "Job %s: OCR requested but no supported OCR backend is available (detected=%s). Falling back to LibreOffice.",
                job_id,
                ",".join(ocr_backends),
            )
        else:
            logger.info("Job %s: OCR disabled. Skipping scanned check.", job_id)
                
        # Existing LibreOffice logic
        self._run_libreoffice(input_path, output_dir)
        
        filename = os.path.splitext(os.path.basename(input_path))[0]
        lo_output = os.path.join(output_dir, f"{filename}.docx")
        
        if os.path.exists(lo_output):
             if lo_output != output_path:
                 if os.path.exists(output_path):
                     os.remove(output_path)
                 os.rename(lo_output, output_path)
        else:
             raise ConversionError(f"LibreOffice conversion failed output not found at {lo_output}")
             
        return output_path

    def convert_to_pdf(self, input_path: str, job_id: str) -> str:
        """
        Convert input file to PDF.
        Crucial for enabling AI analysis (GROBID/Docling) on DOCX inputs.
        
        Args:
            input_path: Path to source file
            job_id: Unique job identifier
            
        Returns:
            Path to the resulting .pdf file
        """
        input_path = os.path.abspath(input_path)
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        job_dir = os.path.join(self.temp_dir, str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        
        # Predict Output Path
        input_name = Path(input_path).stem
        output_path = os.path.join(job_dir, "input.pdf")
        
        # If input is already PDF, just copy it
        if input_path.lower().endswith(".pdf"):
            shutil.copy2(input_path, output_path)
            return output_path

        # Use LibreOffice for high-fidelity conversion
        self._run_libreoffice_to_pdf(input_path, job_dir)
        
        # LibreOffice output handling
        # It usually outputs [filename].pdf in the output dir
        lo_output = os.path.join(job_dir, f"{input_name}.pdf")
        
        if os.path.exists(lo_output):
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            os.rename(lo_output, output_path)
            return output_path
        else:
            raise ConversionError(f"LibreOffice failed to generate PDF at {lo_output}")

    def _run_libreoffice_to_pdf(self, input_path: str, output_dir: str):
        """Convert to PDF using LibreOffice (headless)."""
        soffice = self._get_libreoffice_cmd()
        
        if not soffice:
            raise ConversionError("LibreOffice not installed or not in PATH")
            
        try:
            # soffice --headless --convert-to pdf input.docx --outdir ...
            cmd = [
                soffice,
                "--headless",
                "--convert-to", "pdf",
                input_path,
                "--outdir", output_dir
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            raise ConversionError("LibreOffice PDF conversion timed out after 180 seconds")
        except subprocess.CalledProcessError as exc:
            raise ConversionError(f"LibreOffice PDF conversion failed: {exc.stderr.decode() if exc.stderr else str(exc)}")

    def _run_pandoc(self, input_path: str, output_path: str):
        """
        Convert using Pandoc.
        Used strictly as a format conversion layer (e.g., tex/md -> docx).
        Structure and styles are NOT assumed to be reliable here; 
        they are inferred later in the pipeline.
        """
        if not shutil.which("pandoc"):
             raise ConversionError("Pandoc not installed or not in PATH")
             
        try:
            # pandoc input.md -o output.docx
            cmd = ["pandoc", input_path, "-o", output_path]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            raise ConversionError("Pandoc conversion timed out after 120 seconds")
        except subprocess.CalledProcessError as exc:
            raise ConversionError(f"Pandoc conversion failed: {exc.stderr.decode() if exc.stderr else str(exc)}")

    def _run_libreoffice(self, input_path: str, output_dir: str):
        """Convert using LibreOffice (headless)."""
        # Determine command name (platform dependent)
        soffice = self._get_libreoffice_cmd()
        
        if not soffice:
            raise ConversionError("LibreOffice not installed or not in PATH")
            
        try:
            # soffice --headless --convert-to docx input.pdf --outdir ...
            cmd = [
                soffice,
                "--headless",
                "--convert-to", "docx",
                input_path,
                "--outdir", output_dir
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            raise ConversionError("LibreOffice conversion timed out after 180 seconds")
        except subprocess.CalledProcessError as exc:
            raise ConversionError(f"LibreOffice conversion failed: {exc.stderr.decode() if exc.stderr else str(exc)}")

    def _get_libreoffice_cmd(self) -> Optional[str]:
        # Common command names
        candidates = ["soffice", "libreoffice"]
        if os.name == 'nt': # Windows
            # Check common paths if not in PATH
            candidates.extend([
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ])
            
        for cmd in candidates:
            if shutil.which(cmd):
                return cmd
            if os.name == 'nt' and os.path.exists(cmd):
                return cmd
                
        return None
