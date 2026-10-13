"""
System tray integration for TimeLord using pystray.
Runs in a separate thread to avoid blocking the NiceGUI event loop.
"""
import threading
from typing import Callable, Optional

import pystray
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw


class SystemTray:
    """
    System tray icon manager for TimeLord.
    
    Provides:
    - Tray icon with status indicator
    - Show/Hide window menu
    - Quit application menu
    """
    
    def __init__(self, on_show: Optional[Callable] = None, on_quit: Optional[Callable] = None):
        """
        Initialize the system tray.
        
        Args:
            on_show: Callback when user clicks 'Show' from tray menu.
            on_quit: Callback when user clicks 'Quit' from tray menu.
        """
        self.on_show = on_show
        self.on_quit = on_quit
        self._icon: Optional[Icon] = None
        self._thread: Optional[threading.Thread] = None
        
    def _create_icon_image(self) -> Image:
        """
        Create a simple icon image programmatically.
        Returns a green circle icon for active status.
        """
        size = (64, 64)
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a green circle (active indicator)
        draw.ellipse([4, 4, 60, 60], fill=(76, 175, 80, 255))  # Material Green 500
        
        # Draw a clock hand
        draw.line([32, 32, 32, 16], fill=(255, 255, 255, 255), width=4)
        draw.line([32, 32, 44, 32], fill=(255, 255, 255, 255), width=4)
        
        return image
    
    def _on_tray_click(self, icon: Icon, item: MenuItem):
        """Handle tray icon click - show window."""
        if self.on_show:
            self.on_show()
    
    def _create_menu(self) -> Menu:
        """Create the tray context menu."""
        return Menu(
            MenuItem('Show TimeLord', action=lambda icon, item: self.on_show() if self.on_show else None),
            MenuItem('Hide', action=lambda icon, item: icon.hide()),
            Menu.SEPARATOR,
            MenuItem('Quit', action=lambda icon, item: self._quit(icon)),
        )
    
    def _quit(self, icon: Icon):
        """Quit the application."""
        icon.stop()
        if self.on_quit:
            self.on_quit()
    
    def start(self):
        """Start the system tray icon in a background thread."""
        def run_tray():
            self._icon = Icon(
                "TimeLord",
                self._create_icon_image(),
                "ActiveWindow Time Tracker",
                menu=self._create_menu()
            )
            self._icon.run()
        
        self._thread = threading.Thread(target=run_tray, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the system tray icon."""
        if self._icon:
            self._icon.stop()
        if self._thread:
            self._thread.join(timeout=2.0)
    
    def set_status(self, status: str):
        """
        Update the tray icon tooltip status.
        
        Args:
            status: Status text to display.
        """
        if self._icon:
            self._icon.title = f"TimeLord - {status}"
