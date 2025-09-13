#!/usr/bin/env python3

import sys
import threading
import webbrowser
import os
import winreg
from pathlib import Path
import io
import base64

import pystray
from PIL import Image, ImageDraw
from flask import Flask
import logging

from brightness_server import app, brightness_controller, CONFIG, logger

class BrightnessTrayApp:
    def __init__(self):
        self.server_thread = None
        self.tray_icon = None
        self.is_running = False
        
        self.icon_image = self.create_icon()
        self.setup_logging()
        
    def create_icon(self):
        width = height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        center = width // 2
        radius = 20
        
        # Sun icon
        draw.ellipse([center-radius//2, center-radius//2, 
                     center+radius//2, center+radius//2], 
                     fill='orange')
        
        # Sun rays
        for i in range(8):
            angle = i * 45
            import math
            x1 = center + radius * 0.8 * math.cos(math.radians(angle))
            y1 = center + radius * 0.8 * math.sin(math.radians(angle))
            x2 = center + radius * 1.3 * math.cos(math.radians(angle))
            y2 = center + radius * 1.3 * math.sin(math.radians(angle))
            draw.line([x1, y1, x2, y2], fill='orange', width=3)
        
        return image
    
    def setup_logging(self):
        if sys.stdout is None or not sys.stdout.isatty():
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    def start_server(self):
        try:
            logger.info("Starting brightness server...")
            app.run(
                host=CONFIG['host'],
                port=CONFIG['port'],
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
    
    def get_current_brightness(self):
        try:
            return brightness_controller.get_current_brightness()
        except:
            return "N/A"
    
    def set_brightness_manual(self, value):
        try:
            brightness_controller.set_brightness(value)
            logger.info(f"Manual brightness set: {value}%")
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
    
    def toggle_autostart(self):
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            app_name = "BrightnessSync"
            exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                              winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
                try:
                    winreg.QueryValueEx(key, app_name)
                    winreg.DeleteValue(key, app_name)
                    logger.info("Autostart disabled")
                    return False
                except FileNotFoundError:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                    logger.info("Autostart enabled")
                    return True
        except Exception as e:
            logger.error(f"Autostart error: {e}")
            return None
    
    def is_autostart_enabled(self):
        try:
            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            app_name = "BrightnessSync"
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, 
                              winreg.KEY_QUERY_VALUE) as key:
                winreg.QueryValueEx(key, app_name)
                return True
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def open_web_interface(self):
        url = f"http://localhost:{CONFIG['port']}/health"
        webbrowser.open(url)
    
    def create_menu(self):
        current_brightness = self.get_current_brightness()
        autostart_enabled = self.is_autostart_enabled()
        
        return pystray.Menu(
            pystray.MenuItem(f"Current brightness: {current_brightness}%", None, enabled=False),
            pystray.Menu.SEPARATOR,
            
            # Quick brightness settings
            pystray.MenuItem("Set brightness", pystray.Menu(
                pystray.MenuItem("10%", lambda: self.set_brightness_manual(10)),
                pystray.MenuItem("25%", lambda: self.set_brightness_manual(25)),
                pystray.MenuItem("50%", lambda: self.set_brightness_manual(50)),
                pystray.MenuItem("75%", lambda: self.set_brightness_manual(75)),
                pystray.MenuItem("100%", lambda: self.set_brightness_manual(100)),
            )),
            
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Auto brightness", 
                           lambda: brightness_controller.set_brightness(
                               brightness_controller.get_time_based_brightness())),
            pystray.Menu.SEPARATOR,
            
            pystray.MenuItem(f"Autostart {'✓' if autostart_enabled else ''}",
                           self.toggle_autostart),
            pystray.MenuItem("Open web interface", self.open_web_interface),
            pystray.MenuItem("Open logs folder", self.open_logs_folder),
            
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )
    
    def open_logs_folder(self):
        log_path = Path(__file__).parent
        os.startfile(log_path)
    
    def quit_app(self):
        logger.info("Shutting down...")
        self.is_running = False
        if self.tray_icon:
            self.tray_icon.stop()
    
    def run(self):
        logger.info("Starting brightness sync app...")
        
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        self.tray_icon = pystray.Icon(
            "BrightnessSync",
            self.icon_image,
            "Brightness Sync",
            self.create_menu()
        )
        
        self.is_running = True
        
        # Update menu every 30 seconds
        def update_menu():
            import time
            while self.is_running:
                time.sleep(30)
                if self.tray_icon and self.is_running:
                    self.tray_icon.menu = self.create_menu()
        
        update_thread = threading.Thread(target=update_menu, daemon=True)
        update_thread.start()
        
        try:
            self.tray_icon.run()
        except KeyboardInterrupt:
            self.quit_app()

def main():
    # Check if server is already running
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', CONFIG['port']))
        sock.close()
        
        if result == 0:
            print("Server already running!")
            sys.exit(1)
    except:
        pass
    
    app_instance = BrightnessTrayApp()
    app_instance.run()

if __name__ == "__main__":
    main()