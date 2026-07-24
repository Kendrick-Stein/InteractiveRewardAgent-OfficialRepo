"""
RewardAgent tools package.

Provides tools for trajectory analysis and environment state verification.
"""

from .CaptionImage import CaptionImageTool
from .CheckExcelFile import CheckExcelFileTool
from .CheckPptFile import CheckPptFileTool
from .CheckWordFile import CheckWordFileTool
from .GetPptXml import GetPptXmlTool

# Thunderbird tools re-exports (optional convenience)
# Thunderbird tools re-exports (optional convenience; tolerate missing deps)
try:
    from .thunderbird import (
        GetThunderbirdPrefsFileTool,
        GetThunderbirdActiveThemeTool,
        GetThunderbirdRegionTool,
        GetThunderbirdTimezoneTool,
        GetThunderbirdUseSystemTimezoneTool,
        GetThunderbirdAccountsTool,
        GetThunderbirdImapServerInfoTool,
        GetThunderbirdSmtpServerInfoTool,
    )
    _THUNDERBIRD_AVAILABLE = True
except Exception as _th_e:
    _THUNDERBIRD_AVAILABLE = False

# Lazy import of environment tools to avoid dependency issues
# from .environment_tools import (...)

# VS Code getters (optional convenience re-export)
from .vscode_getters import (
    GetVSCodeUserSettingsFileTool,
    GetVSCodeSettingValueByIntentTool,
    GetVSCodeExtensionsTool,
    GetVSCodeKeybindingsFileTool,
    CheckVSCodeKeybindingByIntentTool,
    # GetVSCodeWorkspaceFileTool,
    GetVSCodeWorkspaceSettingValueByIntentTool,
)

__all__ = [
    'CaptionImageTool',
    'CheckExcelFileTool',
    'CheckPptFileTool',
    'CheckWordFileTool',
    'GetPptXmlTool',
    # VS Code getters
    'GetVSCodeUserSettingsFileTool',
    'GetVSCodeSettingValueByIntentTool',
    'GetVSCodeExtensionsTool',
    'GetVSCodeKeybindingsFileTool',
    'CheckVSCodeKeybindingByIntentTool',
    # 'GetVSCodeWorkspaceFileTool',
    'GetVSCodeWorkspaceSettingValueByIntentTool',
    # Environment tools are imported lazily when needed
    # 'VMCommandLineTool',
    # 'VMCommandErrorTool',
    # 'VMFileTool',
    # 'VMTerminalOutputTool',
    # 'GetActiveURLTool',
]

# Conditionally extend with Thunderbird tools if available
if _THUNDERBIRD_AVAILABLE:
    __all__.extend([
        'GetThunderbirdPrefsFileTool',
        'GetThunderbirdActiveThemeTool',
        'GetThunderbirdRegionTool',
        'GetThunderbirdTimezoneTool',
        'GetThunderbirdUseSystemTimezoneTool',
        'GetThunderbirdAccountsTool',
        'GetThunderbirdImapServerInfoTool',
        'GetThunderbirdSmtpServerInfoTool',
    ])
