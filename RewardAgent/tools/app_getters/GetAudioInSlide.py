from smolagents import Tool
from desktop_env.evaluators.getters.impress import get_audio_in_slide


class GetAudioInSlideTool(Tool):
    name = "get_audio_in_slide"
    description = """Extract audio file from a PowerPoint slide.
    
    This tool extracts audio files embedded in or linked to a specific slide
    in a PowerPoint presentation (.pptx file). It analyzes the slide's XML
    relationships to locate and extract audio content.
    """
    inputs = {
        "ppt_file_path": {
            "type": "string", 
            "description": "Path to the PowerPoint (.pptx) file on the Virtual Machine (VM)"
        },
        "slide_index": {
            "type": "string", 
            "description": "Index of the slide (0-based) to extract audio from"
        },
        "dest": {
            "type": "string", 
            "description": "Destination filename for the extracted audio file (will be saved to host)"
        }
    }
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, ppt_file_path: str, slide_index: str, dest: str) -> str:
        """Extract audio file from PowerPoint slide on the Virtual Machine.
        
        Args:
            ppt_file_path: Path to the PowerPoint file on the Virtual Machine (VM)
            slide_index: Index of the slide (0-based)
            dest: Destination filename for the audio file to be saved to host
            
        Returns:
            str: Path to the extracted audio file, or None if not found
        """
        try:
            config = {
                "ppt_file_path": ppt_file_path,
                "slide_index": slide_index,
                "dest": dest
            }
            result = get_audio_in_slide(self.env, config)
            if result is None:
                return "Error: No audio file found in the specified slide"
            return result
        except Exception as e:
            return f"Error: Failed to extract audio file: {str(e)}"

    def __call__(self, ppt_file_path: str, slide_index: str, dest: str) -> str:
        return self.forward(ppt_file_path, slide_index, dest)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to extract audio files from PowerPoint slides.
Example usage:
- get_audio_in_slide(ppt_file_path="/path/to/xxx.pptx", slide_index="0", dest="slide1_audio.mp3")
- get_audio_in_slide(ppt_file_path="/path/to/xxx.pptx", slide_index="2", dest="narration.wav")

Note: ppt_file_path should be the path on the Virtual Machine (VM).
The tool returns the path to the extracted audio file in the host."""
