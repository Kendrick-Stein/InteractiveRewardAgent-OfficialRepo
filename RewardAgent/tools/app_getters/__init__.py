"""Application-specific getter tools for RewardAgent."""

# Accessibility (always-on)
from .GetAccessibilityTree import GetAccessibilityTreeTool

# VLC tools
# from .CompareAudios import CompareAudiosTool  # removed from default export per design
from .GetVLCPlayingInfo import GetVLCPlayingInfoTool
from .GetVLCConfig import GetVLCConfigTool
from .GetDefaultVideoPlayer import GetDefaultVideoPlayerTool

# GIMP tools
from .GetGimpConfigFile import GetGimpConfigFileTool

# LibreOffice Impress tools (kept minimal)
# from .GetBackgroundImageInSlide import GetBackgroundImageInSlideTool  # not default-loaded
# from .GetAudioInSlide import GetAudioInSlideTool  # not default-loaded

__all__ = [
    # Accessibility
    "GetAccessibilityTreeTool",
    # VLC
    "GetVLCPlayingInfoTool",
    "GetVLCConfigTool", 
    "GetDefaultVideoPlayerTool",
    # "CompareAudiosTool",  # intentionally omitted from default
    # GIMP
    "GetGimpConfigFileTool",
    # LibreOffice Impress minimal set (none exported by default here)
]
