# Updated implementation with interactive square selection and swiping using index finger.
# - Squares are now individual objects that can be selected by pointing with index finger (overlapping).
# - Once selected, the square attaches to the index finger tip and moves with it.
# - If swiped off-screen in the correct direction (host: right, client: left), it's sent.
# - On receive, a new square animates in from the opposite side to the bottom row.
# - If hand disappears while holding, the square drops back to the row.
# - No speed check for swipe; just off-screen detection. Adjust as needed.
# - Install dependencies: pip install opencv-python mediapipe.

import cv2
import mediapipe as mp
import socket
import threading
import time

# Game settings
INITIAL_SQUARES = 10
SQUARE_SIZE = 50
SQUARE_COLOR = (0, 255, 0)
ANIMATION_SPEED = 20  # Pixels per frame for incoming squares
PORT = 12345

# Square class
class Square:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# Global variables
own_squares = []
selected_square = None
game_over = False
is_host = False

# Receiver thread to handle incoming messages
def receiver(conn, width, height):
    global own_squares, game_over
    while not game_over:
        try:
            data = conn.recv(1024).decode()
            if data == 'send':
                # Add incoming square
                if is_host:
                    start_x = -SQUARE_SIZE  # From left
                else:
                    start_x = width  # From right
                start_y = height - SQUARE_SIZE - 20
                new_sq = Square(start_x, start_y)
                new_sq.is_incoming = True
                new_sq.target_x = get_next_position(width)
                new_sq.target_y = start_y
                own_squares.append(new_sq)
                print(f"Received a square! Now have {len(own_squares)} remaining.")
            elif data == 'win':
                print("You lost! The other player won.")
                game_over = True
        except:
            break

# Calculate the position for the next square in the row
def get_next_position(width):
    num = len(own_squares) + 1
    start_x = (width - (SQUARE_SIZE * num + 10 * (num - 1))) // 2
    return start_x + (num - 1) * (SQUARE_SIZE + 10)

# Arrange non-moving squares in the bottom row
def arrange_squares(width, height):
    num = len(own_squares)
    start_x = (width - (SQUARE_SIZE * num + 10 * (num - 1))) // 2
    y = height - SQUARE_SIZE - 20
    for i, sq in enumerate(own_squares):
        if selected_square != i and (not hasattr(sq, 'is_incoming') or not sq.is_incoming):
            sq.x = start_x + i * (SQUARE_SIZE + 10)
            sq.y = y

# Main function
def main():
    global own_squares, selected_square, game_over, is_host

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

    # Setup webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize squares
    num = INITIAL_SQUARES
    start_x = (width - (SQUARE_SIZE * num + 10 * (num - 1))) // 2
    y = height - SQUARE_SIZE - 20
    for i in range(num):
        x = start_x + i * (SQUARE_SIZE + 10)
        own_squares.append(Square(x, y))

    # Start receiver thread (pass width/height for incoming positions)
    recv_thread = threading.Thread(target=receiver, args=(conn, width, height))
    recv_thread.start()

    # Setup MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils

    while not game_over:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip the frame horizontally for a mirror effect
        frame = cv2.flip(frame, 1)

        # Process for hands
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        hand_detected = results.multi_hand_landmarks is not None

        if hand_detected:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                # Get index finger tip position (denormalized)
                index_lm = hand_lms.landmark[8]
                index_x = index_lm.x * width
                index_y = index_lm.y * height

                # Select square if none selected and overlapping
                if selected_square is None:
                    for i, sq in enumerate(own_squares):
                        if sq.x < index_x < sq.x + SQUARE_SIZE and sq.y < index_y < sq.y + SQUARE_SIZE:
                            selected_square = i
                            break

                # Move selected square with finger
                if selected_square is not None and selected_square < len(own_squares):
                    own_squares[selected_square].x = index_x - SQUARE_SIZE / 2
                    own_squares[selected_square].y = index_y - SQUARE_SIZE / 2

                    # Check if swiped off-screen
                    if (is_host and own_squares[selected_square].x + SQUARE_SIZE > width) or \
                       (not is_host and own_squares[selected_square].x < 0):
                        conn.send('send'.encode())
                        print(f"Sent a square! Remaining: {len(own_squares) - 1}")
                        del own_squares[selected_square]
                        if len(own_squares) == 0:
                            conn.send('win'.encode())
                            print("You won!")
                            game_over = True
                        selected_square = None
        else:
            # No hand detected: drop selected square
            if selected_square is not None:
                selected_square = None

        # Animate incoming squares
        for sq in own_squares:
            if hasattr(sq, 'is_incoming') and sq.is_incoming:
                if is_host:
                    sq.x += ANIMATION_SPEED
                    if sq.x >= sq.target_x:
                        sq.x = sq.target_x
                        sq.y = sq.target_y
                        delattr(sq, 'is_incoming')
                        delattr(sq, 'target_x')
                        delattr(sq, 'target_y')
                else:
                    sq.x -= ANIMATION_SPEED
                    if sq.x <= sq.target_x:
                        sq.x = sq.target_x
                        sq.y = sq.target_y
                        delattr(sq, 'is_incoming')
                        delattr(sq, 'target_x')
                        delattr(sq, 'target_y')

        # Arrange non-moving squares
        arrange_squares(width, height)

        # Draw squares
        for sq in own_squares:
            cv2.rectangle(frame, (int(sq.x), int(sq.y)), (int(sq.x + SQUARE_SIZE), int(sq.y + SQUARE_SIZE)), SQUARE_COLOR, -1)

        # Display game status on frame
        status_text = f"Remaining squares: {len(own_squares)}"
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