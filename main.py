# Updated implementation with visual squares and differentiated swipe directions.
# - Draws a row of squares at the bottom of the window representing remaining squares.
# - Host swipes right to send (positive delta_x).
# - Client swipes left to send (negative delta_x).
# - Swipe detection is global (anywhere in frame), but you can extend to per-square by checking hand position overlaps with a square before swipe.
# - On send, removes the last square visually (simulates sending one).
# - Other changes: Improved stability, added win/lose handling on both sides.

import cv2
import mediapipe as mp
import socket
import threading
import time

# Game settings
INITIAL_SQUARES = 10
SQUARE_SIZE = 50
SQUARE_COLOR = (0, 255, 0)
PORT = 12345

# Global variables
remaining_squares = INITIAL_SQUARES
game_over = False
is_host = False

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

# Draw squares at the bottom of the frame
def draw_squares(frame):
    height, width = frame.shape[:2]
    start_x = (width - (SQUARE_SIZE * remaining_squares + 10 * (remaining_squares - 1))) // 2
    for i in range(remaining_squares):
        x1 = start_x + i * (SQUARE_SIZE + 10)
        y1 = height - SQUARE_SIZE - 20
        x2 = x1 + SQUARE_SIZE
        y2 = height - 20
        cv2.rectangle(frame, (x1, y1), (x2, y2), SQUARE_COLOR, -1)

# Main function
def main():
    global remaining_squares, game_over, is_host

    # Setup socket based on mode
    mode = input("Are you the host (type 'host') or client (type 'client')? ").strip().lower()
    if mode == 'host':
        is_host = True
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
                        # Detect swipe based on role
                        swipe_detected = False
                        if is_host:
                            # Host swipes right: positive delta_x
                            if delta_x > 0.15 and speed > 1.5:  # Adjust thresholds
                                swipe_detected = True
                        else:
                            # Client swipes left: negative delta_x
                            if delta_x < -0.15 and speed > 1.5:
                                swipe_detected = True

                        if swipe_detected and remaining_squares > 0:
                            remaining_squares -= 1
                            conn.send('send'.encode())
                            print(f"Sent a square! Remaining: {remaining_squares}")
                            if remaining_squares == 0:
                                conn.send('win'.encode())
                                print("You won!")
                                game_over = True

                prev_pos = curr_pos
                prev_time = curr_time

        # Draw visual squares
        draw_squares(frame)

        # Display game status on frame
        status_text = f"Remaining squares: {remaining_squares}"
        if is_host:
            status_text += " (Swipe right to send)"
        else:
            status_text += " (Swipe left to send)"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Swipe Game', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()