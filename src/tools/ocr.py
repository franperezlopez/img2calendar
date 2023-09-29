from typing import Any, Dict, Optional

import numpy as np
from azure.ai.formrecognizer import AnalysisFeature
from langchain.tools.azure_cognitive_services import AzureCogsFormRecognizerTool
from langchain.tools.azure_cognitive_services.utils import detect_file_src_type

from src.utils import cached


class OcrTool(AzureCogsFormRecognizerTool):
    name: str = "ocr"
    result: Optional[Any] = None
    enable_tables: bool = False
    enable_keyvalue: bool = False
    enable_barcode: bool = True
    description: str = "OCR tool using Azure Cognitive Services Form Recognizer"
    image : Optional[str] = None
    _model_id = "prebuilt-read"

    def _format_document_analysis_result(self, document_analysis_result: Dict) -> str:
        formatted_result = []
        if document_analysis_result.content is not None:
            full_content = f"{document_analysis_result.content.replace(':barcode:', '').strip()}"

            bboxes = self._build_bboxes(self.result)
            content = max(bboxes, key=lambda x: x['density'])['content']
            full_content = full_content.replace(content, f"*{content}*")
            formatted_result.append(full_content)

        if self.enable_tables and document_analysis_result.tables is not None:
            for i, table in enumerate(document_analysis_result.tables):
                formatted_result.append(f"Table {i}:")
                formatted_result.append(f"{table}".replace("\n", " "))

        if self.enable_keyvalue and document_analysis_result.key_value_pairs is not None:
            for kv_pair in document_analysis_result.key_value_pairs:
                formatted_result.append(
                    f"{kv_pair[0]}: {kv_pair[1]}".replace("\n", " ")
                )

        if self.enable_barcode:
            for page in document_analysis_result.pages:
                for barcode in page.barcodes:
                    formatted_result.append(f"{barcode.kind}: {barcode.value}")

        return "\n".join(formatted_result)

    def _document_analysis(self, document_path: str) -> Dict:
        document_src_type = detect_file_src_type(document_path)
        features = [AnalysisFeature.BARCODES] if self.enable_barcode else None
        if document_src_type == "local":
            with open(document_path, "rb") as document:
                poller = self.doc_analysis_client.begin_analyze_document(self._model_id, document, features=features)
        elif document_src_type == "remote":
            poller = self.doc_analysis_client.begin_analyze_document_from_url(self._model_id, document_path, features=features)
        else:
            raise ValueError(f"Invalid document path: {document_path}")

        self.result = poller.result()
        return self.result

    def _build_bboxes(self, result):
        bboxes = []
        for paragraph in result.paragraphs:
            for bounding_region in paragraph.bounding_regions:
                points = np.array([[pol.x, pol.y] for pol in bounding_region.polygon])
                x_min=np.min(points[:,0])
                x_max=np.max(points[:,0])
                y_min=np.min(points[:,1])
                y_max=np.max(points[:,1])
                rect = {'x': x_min, 'y': y_min,
                        'w': x_max-x_min, 'h': y_max-y_min,
                        'content': paragraph.content,
                        'density': (x_max-x_min)*(y_max-y_min)/len(paragraph.content)}
                bboxes.append(rect)
                # ic(rect)
        return bboxes

    @cached(key_func_name="ocr")
    def _run(self, url: str) -> str:
        """Use the tool."""
        try:
            document_analysis_result = self._document_analysis(url)
            if not document_analysis_result:
                return "No good document analysis result was found"

            return self._format_document_analysis_result(document_analysis_result)
        except Exception as e:
            raise RuntimeError(f"Error while running AzureCogsFormRecognizerTool: {e}")