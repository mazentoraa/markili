# Swipe Game - MARKILI -

A two-player interactive game where players use **hand gestures (via webcam)** to swipe objects (squares or circles) to each other over a network.  
The objective is to send all your designated objects to the other player before time runs out.  

This project was made during the **Integration Day of ISIMM** (Higher Institute of Informatics and Mathematics of Monastir, Tunisia) under the **CPU ISIMM students club**.

---

## 🎮 Features

- **Players**:  
  - Host → sends **squares**  
  - Client → sends **circles**

- **Controls**:  
  - Use your **index finger** to select and swipe objects.  
  - Host swipes **right**, Client swipes **left**.

- **Weapons**:  
  - Earn a weapon after **two consecutive sends without receiving**.  
  - Swipe weapon to freeze opponent for **1 second** (displays `frozen.png` background).

- **Timer**:  
  - Game lasts **60 seconds**.  
  - Win by emptying your objects or having fewer left when time runs out.

- **Restart**:  
  - Press **`r`** anytime to restart.

- **Visuals**:  
  - Squares → `player_one.png`  
  - Circles → `player_two.png`  
  - Weapons → `weapon.png`

- **Network**:  
  - Host automatically displays its **IP address** for client connection.

---

## ⚙️ Prerequisites

- **Python**: 3.10  
- **Libraries**:  
  - `opencv-python`  
  - `mediapipe`  
  - `numpy`  

- **Hardware**:  
  - Webcam on both PCs  
  - Both PCs on the same WiFi network  

---

## 🚀 Setup

1. Ensure required images are in the script directory.  

2. Create and activate a virtual environment:

   ```
   python -m venv venv
   ```
   On Windows: 
   ```
   venv\Scripts\activate
   ```
    
   On Unix or MacOS:
   ```
   source venv/bin/activate
   ```

3. Install dependencies from requirements.txt:
   ```
   pip install -r requirements.txt
   ```

## How to Play

**Start the Host**:
1. Run python main.py.
2. Select 'host' when prompted.
3. Note the displayed IP address (e.g., Host IP address: 192.168.1.100).
4. Wait for the client to connect.

**Start the Client**:
1. Run python main.py on the second PC.
2. Select 'client' and enter the host's IP address.

## Gameplay:
 - Host swipes squares (green or player_one.png) to the right.
 - Client swipes circles (red or player_two.png) to the left.
 - Point index finger to select an object, move to drag, swipe off-screen to send.
 - Swiping wrong object shows a warning.
 - Earn a weapon (blue or weapon.png) after two consecutive sends without receiving.
 - Swipe weapon to freeze opponent (frozen.png background, no hand detection for 1s).
 - Game ends when one player sends all their objects or after 60s (fewer sendable objects wins).

## Controls:
 - Press 'r' to restart.
 - Press 'q' to quit.

## Notes
 - Ensure images are valid (e.g., 100x100 PNGs). Fallback colors used if images fail to load.
 - If host IP isn't detected, use ipconfig (Windows) or ifconfig/ip addr (Linux/Mac).
 - Adjust OBJECT_SIZE, GAME_TIME, or FREEZE_DURATION in the script for customization.

## Troubleshooting
 - **Webcam issues**: Ensure webcam is accessible and not used by another app.
 - **Connection issues**: Verify both PCs are on the same network, firewall allows PORT 12345.
 - **Hand detection**: Ensure good lighting and clear hand visibility.

## Potential Enhancements
 - Add sound effects for sends, freezes, or wins.
 - Display host IP on-screen.
 - Visual feedback for restart (e.g., screen flash).
 - Limit weapon usage or add more mechanics.
