import keyboard
import threading
from pynput import mouse
import logging

logger = logging.getLogger('DFG-Funk')


class HotkeyManager:
    def __init__(self, primary_hotkey, secondary_hotkey, on_press_callback, on_release_callback, 
                 channel1_hotkey=None, channel2_hotkey=None, on_channel_switch_callback=None):
        self.primary_hotkey = primary_hotkey
        self.secondary_hotkey = secondary_hotkey
        self.channel1_hotkey = channel1_hotkey
        self.channel2_hotkey = channel2_hotkey
        self.on_press_callback = on_press_callback
        self.on_release_callback = on_release_callback
        self.on_channel_switch_callback = on_channel_switch_callback
        self.primary_pressed = False
        self.secondary_pressed = False
        self.channel1_pressed = False
        self.channel2_pressed = False
        self.enabled = False
        self.lock = threading.Lock()
        self.mouse_listener = None
        
        # Mouse button mapping
        self.mouse_buttons = {
            'mouse1': mouse.Button.left,
            'mouse2': mouse.Button.right,
            'mouse3': mouse.Button.middle,
            'mouse4': getattr(mouse.Button, 'x1', None),  # Side button 1
            'mouse5': getattr(mouse.Button, 'x2', None),  # Side button 2
        }

    def _on_primary_event(self, event):
        with self.lock:
            if not self.enabled:
                return
            
            if event.event_type == keyboard.KEY_DOWN and not self.primary_pressed:
                print(f"🎤 Primär-Taste gedrückt: {event.name}")
                self.primary_pressed = True
                if self.on_press_callback:
                    self.on_press_callback('primary')
            elif event.event_type == keyboard.KEY_UP and self.primary_pressed:
                print(f"🎤 Primär-Taste losgelassen: {event.name}")
                self.primary_pressed = False
                if self.on_release_callback:
                    self.on_release_callback('primary')
    
    def _on_secondary_event(self, event):
        with self.lock:
            if not self.enabled:
                return
            
            if event.event_type == keyboard.KEY_DOWN and not self.secondary_pressed:
                self.secondary_pressed = True
                if self.on_press_callback:
                    self.on_press_callback('secondary')
            elif event.event_type == keyboard.KEY_UP and self.secondary_pressed:
                self.secondary_pressed = False
                if self.on_release_callback:
                    self.on_release_callback('secondary')
    
    def _on_channel1_event(self, event):
        with self.lock:
            if not self.enabled:
                return
            
            if event.event_type == keyboard.KEY_DOWN and not self.channel1_pressed:
                self.channel1_pressed = True
                if self.on_channel_switch_callback:
                    self.on_channel_switch_callback('channel1')
            elif event.event_type == keyboard.KEY_UP and self.channel1_pressed:
                self.channel1_pressed = False
    
    def _on_channel2_event(self, event):
        with self.lock:
            if not self.enabled:
                return
            
            if event.event_type == keyboard.KEY_DOWN and not self.channel2_pressed:
                self.channel2_pressed = True
                if self.on_channel_switch_callback:
                    self.on_channel_switch_callback('channel2')
            elif event.event_type == keyboard.KEY_UP and self.channel2_pressed:
                self.channel2_pressed = False

    def _is_mouse_button(self, hotkey):
        """Check if hotkey is a mouse button"""
        return hotkey and hotkey.startswith('mouse')
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse button events"""
        if not self.enabled:
            return
        
        # Map button to our naming convention
        button_name = None
        if button == mouse.Button.left:
            button_name = 'mouse1'
        elif button == mouse.Button.right:
            button_name = 'mouse2'
        elif button == mouse.Button.middle:
            button_name = 'mouse3'
        elif hasattr(mouse.Button, 'x1') and button == mouse.Button.x1:
            button_name = 'mouse4'
        elif hasattr(mouse.Button, 'x2') and button == mouse.Button.x2:
            button_name = 'mouse5'
        
        if not button_name:
            return
        
        with self.lock:
            # Primary hotkey
            if button_name == self.primary_hotkey:
                if pressed and not self.primary_pressed:
                    logger.info(f"🎤 Primär-Maustaste gedrückt: {button_name}")
                    self.primary_pressed = True
                    if self.on_press_callback:
                        self.on_press_callback('primary')
                elif not pressed and self.primary_pressed:
                    logger.info(f"🎤 Primär-Maustaste losgelassen: {button_name}")
                    self.primary_pressed = False
                    if self.on_release_callback:
                        self.on_release_callback('primary')
            
            # Secondary hotkey
            elif button_name == self.secondary_hotkey:
                if pressed and not self.secondary_pressed:
                    self.secondary_pressed = True
                    if self.on_press_callback:
                        self.on_press_callback('secondary')
                elif not pressed and self.secondary_pressed:
                    self.secondary_pressed = False
                    if self.on_release_callback:
                        self.on_release_callback('secondary')
            
            # Channel 1 hotkey
            elif button_name == self.channel1_hotkey:
                if pressed and not self.channel1_pressed:
                    self.channel1_pressed = True
                    if self.on_channel_switch_callback:
                        self.on_channel_switch_callback('channel1')
                elif not pressed and self.channel1_pressed:
                    self.channel1_pressed = False
            
            # Channel 2 hotkey
            elif button_name == self.channel2_hotkey:
                if pressed and not self.channel2_pressed:
                    self.channel2_pressed = True
                    if self.on_channel_switch_callback:
                        self.on_channel_switch_callback('channel2')
                elif not pressed and self.channel2_pressed:
                    self.channel2_pressed = False

    def enable(self):
        with self.lock:
            if not self.enabled:
                try:
                    logger.info(f"🎹 Registriere Hotkeys: Primär={self.primary_hotkey}, Sekundär={self.secondary_hotkey}")
                    
                    # Register keyboard hotkeys
                    if not self._is_mouse_button(self.primary_hotkey):
                        keyboard.hook_key(self.primary_hotkey, self._on_primary_event)
                    if not self._is_mouse_button(self.secondary_hotkey):
                        keyboard.hook_key(self.secondary_hotkey, self._on_secondary_event)
                    if self.channel1_hotkey and not self._is_mouse_button(self.channel1_hotkey):
                        logger.info(f"   Kanal1={self.channel1_hotkey}")
                        keyboard.hook_key(self.channel1_hotkey, self._on_channel1_event)
                    if self.channel2_hotkey and not self._is_mouse_button(self.channel2_hotkey):
                        logger.info(f"   Kanal2={self.channel2_hotkey}")
                        keyboard.hook_key(self.channel2_hotkey, self._on_channel2_event)
                    
                    # Start mouse listener if any mouse buttons are configured
                    if (self._is_mouse_button(self.primary_hotkey) or 
                        self._is_mouse_button(self.secondary_hotkey) or
                        self._is_mouse_button(self.channel1_hotkey) or
                        self._is_mouse_button(self.channel2_hotkey)):
                        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
                        self.mouse_listener.start()
                        logger.info("🖱️ Maus-Listener aktiviert")
                    
                    self.enabled = True
                    logger.info("✅ Hotkeys aktiviert")
                except Exception as e:
                    logger.error(f"❌ Fehler beim Aktivieren der Hotkeys: {e}")

    def disable(self):
        with self.lock:
            if self.enabled:
                try:
                    # Unhook keyboard keys
                    if not self._is_mouse_button(self.primary_hotkey):
                        keyboard.unhook_key(self.primary_hotkey)
                    if not self._is_mouse_button(self.secondary_hotkey):
                        keyboard.unhook_key(self.secondary_hotkey)
                    if self.channel1_hotkey and not self._is_mouse_button(self.channel1_hotkey):
                        keyboard.unhook_key(self.channel1_hotkey)
                    if self.channel2_hotkey and not self._is_mouse_button(self.channel2_hotkey):
                        keyboard.unhook_key(self.channel2_hotkey)
                    
                    # Stop mouse listener
                    if self.mouse_listener:
                        self.mouse_listener.stop()
                        self.mouse_listener = None
                        logger.info("🖱️ Maus-Listener deaktiviert")
                    
                    logger.info("🔕 Hotkeys deaktiviert")
                except Exception as e:
                    logger.warning(f"⚠️ Fehler beim Deaktivieren der Hotkeys: {e}")
                finally:
                    self.enabled = False
                    self.primary_pressed = False
                    self.secondary_pressed = False
                    self.channel1_pressed = False
                    self.channel2_pressed = False
