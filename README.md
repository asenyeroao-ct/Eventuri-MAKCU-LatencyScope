# Eventuri-MAKCU-LatencyScope

Eventuri-MAKCU LatencyScope measures end-to-end 2PC capture latency across OBS UDP, NDI and capture cards. It watches incoming frames for a configurable color marker, then triggers MAKCU left-click so you can benchmark and compare real input-to-action delay.

## Overview

LatencyScope is a high-performance latency measurement tool designed for two-PC streaming setups. It captures video frames from various sources (OBS UDP streams, NDI, or capture cards), detects a configurable color marker in real-time, and triggers a MAKCU mouse click to measure the complete input-to-action latency chain.

## Features

- **Multiple Capture Sources**
  - OBS UDP (Motion JPEG over UDP)
  - NDI (Network Device Interface)
  - Capture Cards (via DirectShow/MSMF)
  - Screen Capture (BetterCam, DXGI, MSS)

- **High-Performance Color Detection**
  - Configurable color range detection
  - Real-time frame processing
  - Support for multiple detection modes
  - Adjustable tolerance and detection size

- **MAKCU Integration**
  - Automatic MAKCU device detection
  - Serial communication at up to 4M baud
  - Low-latency mouse click triggering
  - Button state monitoring

- **Advanced Configuration**
  - JSON-based configuration
  - Real-time parameter adjustment via GUI
  - Multi-language support (English, Simplified Chinese, Traditional Chinese)
  - Region-based capture and detection

## Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.8 or higher
- **Hardware**:
  - MAKCU device (or compatible serial device)
  - Capture card (optional, for capture card mode)
  - GPU with CUDA support (optional, for GPU-accelerated capture)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Eventuri-MAKCU-LatencyScope.git
cd Eventuri-MAKCU-LatencyScope
```

### 2. Run Setup Script

On Windows, run the setup script to create a virtual environment and install dependencies:

```bash
setup.bat
```

This will:
- Create a Python virtual environment
- Install all required packages from `requirements.txt`
- Configure the environment for optimal performance

### 3. Manual Installation (Alternative)

If you prefer manual setup:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Quick Start

1. **Connect MAKCU Device**
   - Plug in your MAKCU device via USB
   - The application will automatically detect and connect

2. **Configure Capture Source**
   - Edit `config.json` or use the GUI to select capture mode:
     - `capture_card`: Use capture card input
     - `udp`: Receive OBS UDP stream
     - `ndi`: Use NDI source
     - `bettercam`: Screen capture with BetterCam
     - `mss`: Screen capture with MSS
     - `dxgi`: Screen capture with DXGI

3. **Configure Color Detection**
   - Set target color RGB values
   - Adjust tolerance for color matching
   - Configure detection region and size

4. **Run the Application**

```bash
run.bat
```

Or manually:

```bash
venv\Scripts\activate
python main.py
```

### Configuration

The `config.json` file contains all configuration options:

#### Capture Settings

```json
{
  "capture_mode": "capture_card",
  "capture_width": 1920,
  "capture_height": 1080,
  "capture_fps": 240,
  "capture_device_index": 0
}
```

#### Color Detection

```json
{
  "detection_mode": 2,
  "target_color_r": 75,
  "target_color_g": 219,
  "target_color_b": 104,
  "tolerance": 23,
  "detection_size": 27
}
```

#### MAKCU Settings

The MAKCU device is automatically detected. Supported devices include:
- MAKCU (VID:PID 1A86:55D3)
- CH343, CH340, CH347
- CP2102

#### OBS UDP Settings

```json
{
  "udp_ip": "192.168.5.52",
  "udp_port": 1314,
  "target_fps": 240
}
```

## Architecture

### Core Components

- **main.py**: Main application entry point and GUI
- **mouse.py**: MAKCU serial communication and mouse control
- **color_detector.py**: Color detection algorithms
- **config_manager.py**: Configuration management
- **CaptureCard.py**: Capture card interface
- **OBS_UDP.py**: OBS UDP stream receiver
- **ndi_capture.py**: NDI stream receiver
- **bettercam_capture.py**: BetterCam screen capture
- **dxgi_capture.py**: DXGI screen capture
- **mss_capture.py**: MSS screen capture

### Capture Pipeline

1. **Frame Acquisition**: Capture frames from selected source
2. **Region Extraction**: Extract detection region from frame
3. **Color Detection**: Detect target color marker
4. **Trigger Logic**: Process detection and apply cooldown
5. **MAKCU Click**: Send click command via serial

## Performance

- **Capture FPS**: Up to 240+ FPS depending on source
- **Detection Latency**: < 1ms for color detection
- **Serial Latency**: < 1ms at 4M baud
- **Total System Latency**: Measured end-to-end from frame arrival to click execution

## Troubleshooting

### MAKCU Not Detected

- Ensure MAKCU device is connected via USB
- Check device manager for COM port assignment
- Try different USB ports
- Verify device VID:PID matches supported devices

### Low Capture FPS

- Check capture source settings (resolution, FPS)
- For capture cards, verify FourCC format support
- For OBS UDP, check network bandwidth
- For screen capture, ensure GPU acceleration is enabled if available

### Color Detection Not Working

- Verify target color RGB values match your marker
- Adjust tolerance value if detection is too strict/loose
- Check detection region covers the marker area
- Ensure detection size matches marker size

## License

Copyright (c) 2025 asenyeroao-ct  
All rights reserved.

本專案採用嚴格的授權條款。除明確允許的範圍外，所有權利均保留。

**允許的使用：**
- 個人、非商業性質的安裝與使用
- 在不修改、不移除著作權資訊的前提下閱讀與研究

**禁止的行為：**
- 修改或製作衍生作品
- 商業用途
- 重新發布與散佈
- 移除或隱藏著作權聲明

任何超出授權範圍的使用行為，必須事先取得原作者 **書面授權**。

詳細授權條款請參閱 [LICENSE](LICENSE) 文件。

---

Copyright (c) 2025 asenyeroao-ct  
All rights reserved.

This project is licensed under strict terms. All rights are reserved except as explicitly permitted.

**Permitted Use:**
- Personal, non-commercial installation and use
- Reading and studying without modifying or removing copyright notices

**Prohibited Actions:**
- Modification or derivative works
- Commercial use
- Redistribution or re-uploading
- Removal or alteration of copyright information

Any use beyond the permitted scope requires prior **written authorization** from the author.

For full license terms, please see the [LICENSE](LICENSE) file.

## Acknowledgments

- BetterCam for high-performance screen capture
- DXcam for Desktop Duplication API implementation
- OBS Studio for streaming inspiration
- MAKCU project for low-latency input device

## Support

For issues and questions, please open an issue on the GitHub repository.

