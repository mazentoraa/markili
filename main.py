import cv2
import mediapipe as mp
import socket
import threading
import time
import numpy as np

# Game settings
INITIAL_EACH = 5
OBJECT_SIZE = 50
SQUARE_COLOR = (0, 255, 0)
CIRCLE_COLOR = (255, 0, 0)
ANIMATION_SPEED = 20
PORT = 12345
GAME_TIME = 60  # seconds
WARNING_DURATION = 3  # seconds

# Object class
class GameObject:
    def __init__(self, x, y, obj_type):
        self.x = x
        self.y = y
        self.type = obj_type  # 'square' or 'circle'

# Global variables
own_objects = []
selected_object = None
game_over = False
is_host = False
can_send = None  # 'square' or 'circle'
start_time = None
warning_message = ""
warning_start = 0
opponent_sendable = None

# Receiver thread
def receiver(conn, width, height):
    global own_objects, game_over, start_time, opponent_sendable
    while not game_over:
        try:
            data = conn.recv(1024).decode()
            if data == 'start':
                start_time = time.time()
            elif data.startswith('send:'):
                obj_type = data[5:]
                if is_host:
                    start_x = -OBJECT_SIZE
                else:
                    start_x = width
                start_y = height - OBJECT_SIZE - 20
                new_obj = GameObject(start_x, start_y, obj_type)
                new_obj.is_incoming = True
                new_obj.target_x = get_next_position(width)
                new_obj.target_y = start_y
                own_objects.append(new_obj)
                print(f"Received a {obj_type}! Now have {len(own_objects)} objects.")
            elif data == 'win':
                print("You lost! The other player won.")
                game_over = True
            elif data.startswith('timeout:'):
                opponent_sendable = int(data[8:])
                game_over = True
        except:
            break

# Calculate next position
def get_next_position(width):
    num = len(own_objects) + 1
    start_x = (width - (OBJECT_SIZE * num + 10 * (num - 1))) // 2
    return start_x + (num - 1) * (OBJECT_SIZE + 10)

# Arrange non-moving objects
def arrange_objects(width, height):
    num = len([obj for obj in own_objects if not hasattr(obj, 'is_incoming') or not obj.is_incoming])
    start_x = (width - (OBJECT_SIZE * num + 10 * (num - 1))) // 2
    y = height - OBJECT_SIZE - 20
    idx = 0
    for obj in own_objects:
        if selected_object != own_objects.index(obj) and (not hasattr(obj, 'is_incoming') or not obj.is_incoming):
            obj.x = start_x + idx * (OBJECT_SIZE + 10)
            obj.y = y
            idx += 1

# Get sendable count
def get_sendable_count():
    return sum(1 for obj in own_objects if obj.type == can_send)

# Main function
def main():
    global own_objects, selected_object, game_over, is_host, can_send, start_time, warning_message, warning_start, opponent_sendable

    # Setup socket
    mode = input("Are you the host (type 'host') or client (type 'client')? ").strip().lower()
    if mode == 'host':
        is_host = True
        can_send = 'square'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', PORT))
        s.listen(1)
        print("Waiting for client to connect...")
        conn, addr = s.accept()
        print(f"Connected to {addr}")
        conn.send('start'.encode())
        start_time = time.time()
    elif mode == 'client':
        can_send = 'circle'
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

    # Initialize objects: 5 squares, 5 circles
    num = INITIAL_EACH * 2
    start_x = (width - (OBJECT_SIZE * num + 10 * (num - 1))) // 2
    y = height - OBJECT_SIZE - 20
    for i in range(INITIAL_EACH):
        x = start_x + i * (OBJECT_SIZE + 10)
        own_objects.append(GameObject(x, y, 'square'))
    for i in range(INITIAL_EACH):
        x = start_x + (INITIAL_EACH + i) * (OBJECT_SIZE + 10)
        own_objects.append(GameObject(x, y, 'circle'))

    # Start receiver thread
    recv_thread = threading.Thread(target=receiver, args=(conn, width, height))
    recv_thread.start()

    if not is_host:
        # Client waits for 'start'
        while start_time is None:
            time.sleep(0.1)

    # Setup MediaPipe
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
    mp_draw = mp.solutions.drawing_utils
    mp_selfie = mp.solutions.selfie_segmentation
    segmentation = mp_selfie.SelfieSegmentation(model_selection=0)

    # Load background
    bg_image = cv2.imread('player_one.png' if is_host else 'player_two.png')
    if bg_image is None:
        print("Error: Could not load background image. Using black background.")
        bg_image = np.zeros((height, width, 3), dtype=np.uint8)
    else:
        bg_image = cv2.resize(bg_image, (width, height))

    while not game_over:
        ret, frame = cap.read()
        if not ret:
            break

        # Flip frame
        frame = cv2.flip(frame, 1)

        # Selfie segmentation
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        seg_results = segmentation.process(rgb)
        mask = seg_results.segmentation_mask
        condition = np.stack((mask,) * 3, axis=-1) > 0.5  # Adjust threshold if needed
        frame = np.where(condition, frame, bg_image)

        # Process hands
        results = hands.process(rgb)

        hand_detected = results.multi_hand_landmarks is not None

        if hand_detected:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_lms, mp_hands.HAND_CONNECTIONS)

                index_lm = hand_lms.landmark[8]
                index_x = index_lm.x * width
                index_y = index_lm.y * height

                if selected_object is None:
                    for i, obj in enumerate(own_objects):
                        # Overlap check (approx for circle)
                        if obj.x < index_x < obj.x + OBJECT_SIZE and obj.y < index_y < obj.y + OBJECT_SIZE:
                            selected_object = i
                            break

                if selected_object is not None and selected_object < len(own_objects):
                    obj = own_objects[selected_object]
                    obj.x = index_x - OBJECT_SIZE / 2
                    obj.y = index_y - OBJECT_SIZE / 2

                    # Check if swiped off-screen
                    off_screen = (is_host and obj.x + OBJECT_SIZE > width) or (not is_host and obj.x < 0)
                    if off_screen:
                        if obj.type == can_send:
                            conn.send(f'send:{obj.type}'.encode())
                            print(f"Sent a {obj.type}! Remaining objects: {len(own_objects) - 1}")
                            del own_objects[selected_object]
                            sendable_count = get_sendable_count()
                            if sendable_count == 0:
                                conn.send('win'.encode())
                                print("You won!")
                                game_over = True
                            selected_object = None
                        else:
                            warning_message = "Cannot send this shape!"
                            warning_start = time.time()
                            # Bring back on-screen
                            if is_host:
                                obj.x = width - OBJECT_SIZE
                            else:
                                obj.x = 0
        else:
            selected_object = None

        # Animate incoming
        for obj in own_objects:
            if hasattr(obj, 'is_incoming') and obj.is_incoming:
                if is_host:
                    obj.x += ANIMATION_SPEED
                    if obj.x >= obj.target_x:
                        obj.x = obj.target_x
                        obj.y = obj.target_y
                        delattr(obj, 'is_incoming')
                        delattr(obj, 'target_x')
                        delattr(obj, 'target_y')
                else:
                    obj.x -= ANIMATION_SPEED
                    if obj.x <= obj.target_x:
                        obj.x = obj.target_x
                        obj.y = obj.target_y
                        delattr(obj, 'is_incoming')
                        delattr(obj, 'target_x')
                        delattr(obj, 'target_y')

        # Arrange
        arrange_objects(width, height)

        # Draw objects
        for obj in own_objects:
            if obj.type == 'square':
                cv2.rectangle(frame, (int(obj.x), int(obj.y)), (int(obj.x + OBJECT_SIZE), int(obj.y + OBJECT_SIZE)), SQUARE_COLOR, -1)
            else:
                center_x = int(obj.x + OBJECT_SIZE / 2)
                center_y = int(obj.y + OBJECT_SIZE / 2)
                cv2.circle(frame, (center_x, center_y), OBJECT_SIZE // 2, CIRCLE_COLOR, -1)

        # Timer
        if start_time:
            elapsed = time.time() - start_time
            remaining_time = max(0, GAME_TIME - elapsed)
            cv2.putText(frame, f"Time left: {int(remaining_time)}s", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            if remaining_time <= 0 and not game_over:
                local_sendable = get_sendable_count()
                conn.send(f'timeout:{local_sendable}'.encode())
                game_over = True  # Winner determined when both have sent/received

        # Status
        status_text = f"Objects: {len(own_objects)} (Send {can_send}s)"
        if is_host:
            status_text += " (Swipe right)"
        else:
            status_text += " (Swipe left)"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Warning
        if time.time() - warning_start < WARNING_DURATION:
            cv2.putText(frame, warning_message, (width // 2 - 150, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # After timeout, determine winner if opponent_sendable received
        if game_over and opponent_sendable is not None:
            local_sendable = get_sendable_count()
            if local_sendable < opponent_sendable:
                win_text = "You win on timeout!"
            elif local_sendable > opponent_sendable:
                win_text = "You lose on timeout!"
            else:
                win_text = "Tie on timeout!"
            cv2.putText(frame, win_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            print(win_text)

        cv2.imshow('Swipe Game', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    conn.close()

if __name__ == "__main__":
    main()