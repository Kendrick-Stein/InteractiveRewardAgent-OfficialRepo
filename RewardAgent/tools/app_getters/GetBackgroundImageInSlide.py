from smolagents import Tool
from desktop_env.evaluators.getters.impress import get_background_image_in_slide


class GetBackgroundImageInSlideTool(Tool):
    name = "get_background_image_in_slide"
    description = """Extract background image from a PowerPoint slide.
    
    This tool extracts the background image from a specific slide in a PowerPoint
    presentation (.pptx file) located on the Virtual Machine (VM). It analyzes the slide's XML
    relationships to locate and extract the background image, and saves the result to the host.
    """
    inputs = {
        "ppt_file_path": {
            "type": "string", 
            "description": "Path to the PowerPoint (.pptx) file on the Virtual Machine (VM)"
        },
        "slide_index": {
            "type": "string", 
            "description": "Index of the slide (0-based) to extract background from"
        },
        "dest": {
            "type": "string", 
            "description": "Destination filename for the extracted background image (will be saved to host)"
        }
    }
    output_type = "string"

    def __init__(self, env):
        super().__init__()
        self.env = env

    def forward(self, ppt_file_path: str, slide_index: str, dest: str) -> str:
        """Extract background image from PowerPoint slide on the Virtual Machine.
        
        Args:
            ppt_file_path: Path to the PowerPoint file on the Virtual Machine (VM)
            slide_index: Index of the slide (0-based)
            dest: Destination filename for the image
            
        Returns:
            str: Path to the extracted background image file, or None if not found
        """
        try:
            config = {
                "ppt_file_path": ppt_file_path,
                "slide_index": slide_index,
                "dest": dest
            }
            result = get_background_image_in_slide(self.env, config)
            if result is None:
                return "Error: No background image found in the specified slide"
            return result
        except Exception as e:
            return f"Error: Failed to extract background image: {str(e)}"

    def __call__(self, ppt_file_path: str, slide_index: str, dest: str) -> str:
        return self.forward(ppt_file_path, slide_index, dest)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to extract background images from PowerPoint slides.
Example usage:
- get_background_image_in_slide(ppt_file_path="/path/to/xxx.pptx", slide_index="0", dest="bg_slide1.png")
- get_background_image_in_slide(ppt_file_path="/path/to/xxx.pptx", slide_index="2", dest="background.jpg")

Note: ppt_file_path should be the path on the Virtual Machine (VM).
The tool returns the path to the extracted background image file on the host."""
