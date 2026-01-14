"""Color scheme configuration for H.E.N.R.Y. GUI.

Modern dark theme with black/dark grey backgrounds and white/light grey accents.
Edit this file to customize the color scheme.
"""

# Main Background Colors
MAIN_BG = "#1a1a1a"  # Dark charcoal background
FRAME_BG = "#1a1a1a"  # Frame background (same as main)
CANVAS_BG = "#1a1a1a"  # Canvas background (same as main)
FOOTER_BG = "#1a1a1a"  # Footer background

# Text Colors
TEXT_PRIMARY = "#e0e0e0"  # Light grey for primary text
TEXT_SECONDARY = "#b0b0b0"  # Medium grey for secondary text
TEXT_DARK = "#333333"  # Dark text (for light backgrounds, if needed)

# Status Colors
STATUS_CONNECTED = "#50c878"  # Green for connected status
STATUS_DISCONNECTED = "#ff6b6b"  # Soft red for disconnected status

# Face Colors (Smiley, Timer digits, etc.)
FACE_EYE_COLOR = "#e0e0e0"  # Light grey for eyes
FACE_MOUTH_COLOR = "#e0e0e0"  # Light grey for mouth

# Timer Colors
TIMER_DIGIT_ON = "#e0e0e0"  # Light grey for active segments
TIMER_DIGIT_OFF = "#333333"  # Dark grey for inactive segments
TIMER_COLON_COLOR = "#e0e0e0"  # Light grey for colon

# Button Colors
BUTTON_PAUSE = "#5a9fd4"  # Brighter blue for pause button
BUTTON_PLAY = "#28a745"  # Vibrant green for play button
BUTTON_END = "#e74c3c"  # Brighter red for end/stop button
BUTTON_CANCEL = "#7f8c8d"  # Medium grey for cancel button
BUTTON_CONFIRM = "#e74c3c"  # Brighter red for confirm button
BUTTON_OUTLINE = "#ffffff"  # White outline for better contrast

# Dialog Colors
DIALOG_BG = "#2a2a2a"  # Slightly lighter than main background
DIALOG_OUTLINE = "#ffffff"  # White outline for better visibility
DIALOG_TEXT = "#e0e0e0"  # Light grey text

# Notification Colors
NOTIFICATION_BG = "#2a2a2a"  # Slightly lighter than main background
NOTIFICATION_OUTLINE = "#555555"  # Grey outline
NOTIFICATION_ICON_BG = "#ffd700"  # Gold for notification icon
NOTIFICATION_ICON_OUTLINE = "#ccaa00"  # Dark gold outline
NOTIFICATION_TEXT_START = "#b0b0b0"  # Medium grey (fade start)
NOTIFICATION_TEXT_END = "#e0e0e0"  # Light grey (fade end)

# Idea View Colors (if needed)
IDEA_BG = "#2a2a2a"
IDEA_TEXT = "#e0e0e0"

# UI Element Borders/Outlines
OUTLINE_PRIMARY = "#555555"  # Medium grey for primary outlines
OUTLINE_SECONDARY = "#333333"  # Dark grey for secondary outlines

# Special Effects
OVERLAY_ALPHA_START = 240  # For fade effects (start opacity)
OVERLAY_ALPHA_END = 255  # For fade effects (end opacity)

# Notification text fade (RGB values for calculation)
# Fade from medium grey (176, 176, 176) to light grey (224, 224, 224)
NOTIFICATION_TEXT_START_RGB = 176  # Medium grey
NOTIFICATION_TEXT_END_RGB = 224  # Light grey
