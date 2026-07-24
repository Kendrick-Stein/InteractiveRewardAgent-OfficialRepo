"""
Docx single-file check tools (no ground truth required).
"""
from .ContainsPageBreak import ContainsPageBreakTool
from .HasPageNumbersInFooters import HasPageNumbersInFootersTool
from .FirstLineCentered import FirstLineCenteredTool
from .DocxSpacingPattern import DocxSpacingPatternTool
from .DocxConvertedLowercase import DocxConvertedLowercaseTool
from .DocxAlignmentPattern import DocxAlignmentPatternTool
from .DocxStrikeThroughLastParagraph import DocxStrikeThroughLastParagraphTool
from .DocxItalicFontSize14 import DocxItalicFontSize14Tool

__all__ = [
    "ContainsPageBreakTool",
    "HasPageNumbersInFootersTool",
    "FirstLineCenteredTool",
    "DocxSpacingPatternTool",
    "DocxConvertedLowercaseTool",
    "DocxAlignmentPatternTool",
    "DocxStrikeThroughLastParagraphTool",
    "DocxItalicFontSize14Tool",
]
