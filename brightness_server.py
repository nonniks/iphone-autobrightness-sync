#!/usr/bin/env python3

import json
import logging
import time
from datetime import datetime, time as dt_time
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
import screen_brightness_control as sbc


app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('brightness_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    
    # Display calibration for iPhone XR (625 nits) to laptop AUO B156HAN15.H (300 nits)
    'display_calibration': {
        'iphone_max_nits': 625,
        'laptop_max_nits': 300,
        'iphone_gamma': 2.2,
        'laptop_gamma': 2.2,
        'brightness_curve': 'lut',  # linear, logarithmic, perceptual, lut
        'min_brightness': 5,
        'max_brightness': 95,
        
        # Calibration lookup table (iPhone % -> laptop %)
        'calibration_lut': [
            (0.0, 0.05),
            (0.05, 0.10),
            (0.1, 0.18),
            (0.2, 0.32),
            (0.3, 0.45),
            (0.4, 0.58),
            (0.5, 0.68),
            (0.6, 0.75),
            (0.7, 0.82),
            (0.8, 0.88),
            (0.9, 0.92),
            (1.0, 0.95),
        ]
    },
    
    'brightness_ranges': {
        'very_dark': {'min': 5, 'max': 15},
        'dark': {'min': 15, 'max': 30},
        'dim': {'min': 30, 'max': 50},
        'normal': {'min': 50, 'max': 70},
        'bright': {'min': 70, 'max': 90},
        'very_bright': {'min': 90, 'max': 100}
    },
    
    # Time-based auto brightness
    'time_based_brightness': {
        'night': {'start': '22:00', 'end': '06:00', 'level': 'very_dark'},
        'evening': {'start': '18:00', 'end': '22:00', 'level': 'dim'},
        'morning': {'start': '06:00', 'end': '09:00', 'level': 'normal'},
        'day': {'start': '09:00', 'end': '18:00', 'level': 'bright'}
    },
    
    'smooth_transition': True,
    'transition_steps': 10,
    'transition_delay': 0.1
}


class BrightnessController:
    def __init__(self):
        self.current_brightness = self.get_current_brightness()
        logger.info(f"Current brightness: {self.current_brightness}%")
    
    def get_current_brightness(self) -> int:
        try:
            brightness = sbc.get_brightness()
            if isinstance(brightness, list):
                return brightness[0] if brightness else 50
            return brightness or 50
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return 50
    
    def set_brightness(self, target: int, smooth: bool = True):
        target = max(1, min(100, target))
        
        try:
            if smooth and CONFIG['smooth_transition']:
                self._smooth_brightness_change(target)
            else:
                sbc.set_brightness(target)
                self.current_brightness = target
            
            logger.info(f"Brightness set to: {target}%")
            
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            raise
    
    def _smooth_brightness_change(self, target: int):
        current = self.get_current_brightness()
        steps = CONFIG['transition_steps']
        delay = CONFIG['transition_delay']
        
        if current == target:
            return
        
        step_size = (target - current) / steps
        
        for i in range(steps):
            new_brightness = int(current + step_size * (i + 1))
            new_brightness = max(1, min(100, new_brightness))
            
            sbc.set_brightness(new_brightness)
            time.sleep(delay)
        
        sbc.set_brightness(target)
        self.current_brightness = target
    
    def get_brightness_for_level(self, level: str) -> int:
        if level in CONFIG['brightness_ranges']:
            range_config = CONFIG['brightness_ranges'][level]
            return (range_config['min'] + range_config['max']) // 2
        return 50
    
    def calibrate_brightness(self, iphone_brightness: float) -> int:
        import math
        
        cal = CONFIG['display_calibration']
        iphone_brightness = max(0.0, min(1.0, iphone_brightness))
        
        if cal['brightness_curve'] == 'lut':
            # Interpolation using lookup table
            lut = cal['calibration_lut']
            
            for i in range(len(lut) - 1):
                x1, y1 = lut[i]
                x2, y2 = lut[i + 1]
                
                if x1 <= iphone_brightness <= x2:
                    ratio = (iphone_brightness - x1) / (x2 - x1) if x2 != x1 else 0
                    laptop_brightness = y1 + ratio * (y2 - y1)
                    break
            else:
                if iphone_brightness <= lut[0][0]:
                    laptop_brightness = lut[0][1]
                else:
                    laptop_brightness = lut[-1][1]
        
        elif cal['brightness_curve'] == 'perceptual':
            # Perceptual calibration using gamma curves
            iphone_nits = cal['iphone_max_nits'] * pow(iphone_brightness, cal['iphone_gamma'])
            target_nits = min(iphone_nits, cal['laptop_max_nits'])
            laptop_brightness = pow(target_nits / cal['laptop_max_nits'], 1.0 / cal['laptop_gamma'])
        
        elif cal['brightness_curve'] == 'logarithmic':
            if iphone_brightness > 0:
                log_scale = math.log10(iphone_brightness * 9 + 1)
                laptop_brightness = log_scale * (cal['laptop_max_nits'] / cal['iphone_max_nits'])
            else:
                laptop_brightness = 0
        
        else:
            # Linear calibration
            nits_ratio = cal['laptop_max_nits'] / cal['iphone_max_nits']
            laptop_brightness = iphone_brightness * (1 / nits_ratio)
        
        result = laptop_brightness * 100
        result = max(cal['min_brightness'], min(cal['max_brightness'], result))
        
        logger.info(f"Calibration: iPhone {iphone_brightness:.2f} -> laptop {result:.0f}% (method: {cal['brightness_curve']})")
        return int(result)
    
    def get_time_based_brightness(self) -> int:
        now = datetime.now().time()
        
        for period, config in CONFIG['time_based_brightness'].items():
            start_time = dt_time.fromisoformat(config['start'])
            end_time = dt_time.fromisoformat(config['end'])
            
            if period == 'night':
                if now >= start_time or now <= end_time:
                    return self.get_brightness_for_level(config['level'])
            else:
                if start_time <= now <= end_time:
                    return self.get_brightness_for_level(config['level'])
        
        return self.get_brightness_for_level('normal')


brightness_controller = BrightnessController()


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'current_brightness': brightness_controller.get_current_brightness()
    })


@app.route('/brightness', methods=['POST'])
def set_brightness():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        logger.info(f"Received data: {data}")
        
        # Fix for iPhone Shortcuts empty key
        if '' in data and isinstance(data[''], dict):
            data = data['']
            logger.info(f"Fixed Shortcuts data: {data}")
        
        brightness_value = None
        
        if 'brightness' in data:
            brightness = data['brightness']
            # Convert string to number if needed
            if isinstance(brightness, str):
                try:
                    brightness = float(brightness)
                except ValueError:
                    return jsonify({'error': 'Invalid brightness value'}), 400
            
            if isinstance(brightness, (int, float)):
                # Use calibration for iPhone brightness
                if brightness <= 1:
                    brightness_value = brightness_controller.calibrate_brightness(brightness)
                else:
                    brightness_value = brightness_controller.calibrate_brightness(brightness / 100)
        
        elif 'level' in data:
            level = data['level'].lower()
            brightness_value = brightness_controller.get_brightness_for_level(level)
        
        elif 'time_based' in data and data['time_based']:
            brightness_value = brightness_controller.get_time_based_brightness()
        
        elif 'lux' in data:
            lux = data['lux']
            brightness_value = min(100, max(10, int(lux / 50 + 20)))
        
        if brightness_value is None:
            return jsonify({'error': 'Invalid brightness data'}), 400
        
        smooth = data.get('smooth', True)
        brightness_controller.set_brightness(brightness_value, smooth=smooth)
        
        return jsonify({
            'status': 'success',
            'brightness_set': brightness_value,
            'timestamp': datetime.now().isoformat(),
            'previous_brightness': brightness_controller.current_brightness
        })
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/brightness', methods=['GET'])
def get_brightness():
    try:
        current = brightness_controller.get_current_brightness()
        return jsonify({
            'current_brightness': current,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting brightness: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/auto', methods=['POST'])
def auto_brightness():
    try:
        brightness_value = brightness_controller.get_time_based_brightness()
        brightness_controller.set_brightness(brightness_value)
        
        return jsonify({
            'status': 'success',
            'brightness_set': brightness_value,
            'mode': 'time_based',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error setting auto brightness: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/config', methods=['GET'])
def get_config():
    return jsonify(CONFIG)


if __name__ == '__main__':
    logger.info("Starting brightness server...")
    logger.info(f"Server available at: http://{CONFIG['host']}:{CONFIG['port']}")
    logger.info("Available endpoints:")
    logger.info("  POST /brightness - set brightness")
    logger.info("  GET /brightness - get current brightness")
    logger.info("  POST /auto - auto brightness by time")
    logger.info("  GET /health - server health check")
    logger.info("  GET /config - configuration")
    
    app.run(
        host=CONFIG['host'],
        port=CONFIG['port'],
        debug=CONFIG['debug']
    )