# This is a basic implementation of the game you described using OpenCV for gesture detection and sockets for networking.
# Assumptions:
# - Two players on the same WiFi network.
# - Each player swipes left with their hand in front of the webcam to "send" a square.
# - Sending a square decreases your remaining squares and increases the other player's remaining squares (like dumping them to the neighbor).
# - The first player to reduce their remaining squares to 0 wins.
# - Uses MediaPipe for hand detection (install with: pip install mediapipe).
# - Install OpenCV: pip install opencv-python.
# - Run the code on both PCs. One acts as host (server), the other as client.
# - Adjust thresholds for swipe detection as needed (based on your setup).
# - For simplicity, swipes are detected anywhere in the frame (not tied to specific square positions). You can extend it to map hand position to specific squares.
# - Squares are represented by a count, but you could draw visual squares on the screen.

import cv2
import mediapipe as mp
import socket
import threading
import time

# Game settings
INITIAL_SQUARES = 10
PORT = 12345

# Global variables
remaining_squares = INITIAL_SQUARES
game_over = False

# Receiver thread to handle incoming messages
def receiver(conn):
    global remaining_squares, game_over
    while not game_over:
        try:
            data = conn.recv(1024).decode()
            if data == 'send':
                remaining_squares += 1
                print(f"Received a square! Now have {remaining_squares} remaining.")
            elif data == 'win':
                print("You lost! The other player won.")
                game_over = True
        except:
            break

# Main function
def main():
    global remaining_squares, game_over

    # Setup socket based on mode
    mode = input("Are you the host (type 'host') or client (type 'client')? ").strip().lower()
    if mode == 'host':
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', PORT))
        s.listen(1)
        print("Waiting for client to connect...")
        conn, addr = s.accept()
        print(f"Connected to {addr}")
    elif mode == 'client':
        host_ip = input("Enter host IP address: ").strip()
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((host_ip, PORT))
        print("Connected to host.")
    else:
        print("Invalid mode. Exiting.")
        return

    # Start receiver thread
    recv_thread = threading.Thread(target=receiver, args=(conn,))
    recv_thread.start()

    # Setup MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils

    # Setup webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    prev_pos = None
    prev_time = time.time()

    while not game_over:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip the frame horizontally for a mirror effect
        frame = cv2.flip(frame, 1)

        # Process for hands
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                # Use palm base (landmark 0) for position tracking
                palm = hand_lms.landmark[0]
                curr_pos = (palm.x, palm.y)  # Normalized [0,1]
                curr_time = time.time()

                if prev_pos:
                    delta_x = curr_pos[0] - prev_pos[0]
                    dt = curr_time - prev_time
                    if dt > 0:
                        speed = abs(delta_x) / dt
                        # Detect left swipe: negative delta_x (hand moving left in mirrored view), high speed
                        if delta_x < -0.15 and speed > 1.5:  # Adjust thresholds based on testing
                            if remaining_squares > 0:
                                remaining_squares -= 1
                                conn.send('send'.encode())
                                print(f"Sent a square! Remaining: {remaining_squares}")
                                if remaining_squares == 0:
                                    conn.send('win'.encode())
                                    print("You won!")
                                    game_over = True

                prev_pos = curr_pos
                prev_time = curr_time

        # Display game status on frame
        cv2.putText(frame, f"Remaining squares: {remaining_squares}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Swipe Game', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()