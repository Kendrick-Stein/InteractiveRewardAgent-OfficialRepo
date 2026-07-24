import os
from smolagents import Tool
from desktop_env.evaluators.metrics.vlc import compare_audios


class CompareAudiosTool(Tool):
    """
    This tool compares two audio files and returns a similarity score in the range [0, 1], where 0 indicates no similarity and 1 indicates identical audio content.
    It uses MFCC feature extraction and Dynamic Time Warping (DTW) to compare the audio signals.
    """
    name = "compare_audios"
    description = """Compare two audio files in the host and return a similarity score."""
    inputs = {
        "audio_path_1": {
            "type": "string", 
            "description": "Host path to the first audio file to compare"
        },
        "audio_path_2": {
            "type": "string", 
            "description": "Host path to the second audio file to compare"
        }
    }
    output_type = "number"

    def __init__(self, env=None):
        super().__init__()
        self.env = env  # Keep env parameter for consistency with other tools

    def forward(self, audio_path_1: str, audio_path_2: str) -> float:
        """Compare two audio files and return a similarity score.
        
        Args:
            audio_path_1: Host path to the first audio file
            audio_path_2: Host path to the second audio file
            
        Returns:
            float: Similarity score in the range [0, 1]
        """
        if not os.path.exists(audio_path_2):
                    raise FileNotFoundError(
                        f"Host file not found: '{audio_path_2}'. "
                        f"If this file is on the virtual machine, please use 'get_vm_file' to download it to the host first."
                    )
        try:
            result = compare_audios(audio_path_1, audio_path_2)
            return result
        except Exception as e:
            # Log error but return 0.0 as similarity score
            print(f"Error comparing audio files: {str(e)}")
            return 0.0

    def __call__(self, audio_path_1: str, audio_path_2: str) -> float:
        return self.forward(audio_path_1, audio_path_2)

    def to_code_prompt(self) -> str:
        return f"""You can use the {self.name} tool to compare two audio files and get a similarity score.
Example usage:
- compare_audios(audio_path_1="/path/to/audio1.mp3", audio_path_2="/path/to/audio2.mp3")
- compare_audios(audio_path_1="recording1.wav", audio_path_2="recording2.wav")

Note: Both audio_path_1 and audio_path_2 should be host-side file paths.
The tool returns a similarity score between 0 and 1, where 0 means no similarity and 1 means identical audio content."""
