import socket
import threading
import time
import sys
import numpy
import cv2
import queue

TCP_IP = '192.168.1.1'
TCP_PORT = 80
RTSP_PORT = 7070
BUFFER_SIZE = 16384

JFIF_SOI = b'\xff\xd8'
JFIF_EOI = b'\xff\xd9'

FRAME_CONTROL_HEADER = b'\x05\x33\x8b\x11'

FRAME_HEADER_LEN = 11

FRAME_COMMAND_POS = 4
FRAME_HEADER_LENGTH_POS = 6
FRAME_IMAGE_LENGTH_MSB_POS = 6
FRAME_IMAGE_LENGTH_LSB_POS = 7
FRAME_IMAGE_SOI_OFFSET = 17

FRAME_COMMAND_ENABLE_STREAM = 0x0e
FRAME_COMMAND_IMAGE = 0x25

# This is the smallest message we can send to get images flowing
MSG_1 = b'\x05\x33\x8b\x11\x00\x00\x00\x00\x00\x00'
MSG_2 = b'\x05\x33\x8b\x11\x02\x00\x12\x00\x00\x00\x06\xba\x49\x88\xd5\x21\xea\x12\x64\x01\xdc\xf4\xbb\x5d\x48\x6d\x93\xbc'
MSG_3 = b'\x05\x33\x8b\x11\x2f\x00\x01\x00\x00\x00\x00\x05\x33\x8b\x11\x05\x00\x00\x00\x00\x00'

START_STREAM_MSG = b'\x05\x33\x8b\x11\x0e\x00\x04\x00\x00\x00\x00\x00\x00\x00'

def send_thread():
    rtsp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_sock.connect((TCP_IP, RTSP_PORT))


def recv_thread(frame_queue):
    print("Starting receive thread")
    image_frame_len = 0
    framebuffer = None

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_IP, TCP_PORT))
        sock.send(MSG_1)
        sock.send(MSG_2)
        sock.send(MSG_3)

        sock.send(START_STREAM_MSG)
    except:
        e = sys.exc_info()[0]
        print("Failed to setup socket", e)
        return

    while True:
        try:
            packet = sock.recv(BUFFER_SIZE)
        except:
            e = sys.exc_info()[0]
            print("socket failed, retrying", e)

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((TCP_IP, TCP_PORT))
            sock.send(START_STREAM_MSG)
            continue

        while len(packet) > 0:
            if image_frame_len == 0:
                ctrl_header_pos = packet.find(FRAME_CONTROL_HEADER)

                if ctrl_header_pos == -1:
                    break;

                ctrl_header_end = ctrl_header_pos + FRAME_HEADER_LEN
                ctrl_header = packet[ctrl_header_pos:ctrl_header_end]
                print("Ctrl header" , ctrl_header.hex(), " end: ", ctrl_header_end)

                frame_command = ctrl_header[FRAME_COMMAND_POS]
                if frame_command == FRAME_COMMAND_IMAGE:
                    # Relative packet
                    image_start_pos = ctrl_header_pos + FRAME_HEADER_LEN

                    image_frame_len = int.from_bytes(ctrl_header[FRAME_IMAGE_LENGTH_MSB_POS:FRAME_IMAGE_LENGTH_LSB_POS + 1], "little") - 1
                    print("Frame image length: ", ctrl_header[FRAME_IMAGE_LENGTH_MSB_POS:FRAME_IMAGE_LENGTH_LSB_POS + 1].hex(), " ", image_frame_len)

                    image_frame_end = image_start_pos + image_frame_len

                    print("image frame start:", image_start_pos, "image frame len", image_frame_len, "ends", image_frame_end, "first bytes:", packet[image_start_pos:image_start_pos + 2].hex(), "last bytes:", packet[image_frame_end - 2: image_frame_end].hex())

                    if packet[image_start_pos + FRAME_IMAGE_SOI_OFFSET : image_start_pos + FRAME_IMAGE_SOI_OFFSET + 2] == JFIF_SOI:
                        ts = time.time()
#                        filename = "frame_" + str(ts) + ".jpg"
#                        frame = open(filename, "wb")
                        framebuffer = bytearray()

                        # Skip header before SOI marker
                        image_frame_len = image_frame_len - FRAME_IMAGE_SOI_OFFSET
                        image_start_pos = image_start_pos + FRAME_IMAGE_SOI_OFFSET
                        print("Skipping header. Starting at: ", packet[image_start_pos : image_start_pos + 2].hex(), "image frame len:", image_frame_len)

                    elif framebuffer == None:
                        print("Did not find JFIF SOF, dumping packet:", packet.hex())
                        return

                    # Sometimes image frame overlaps multiple network packets
                    print ("image frame length: " , image_frame_len, " rest of packet: ", len(packet[image_start_pos:]))
                    if image_frame_len > len(packet[image_start_pos:]):
                        print("Image frame overlaps packet")
                        # frame.write(packet[image_start_pos:])
                        framebuffer.extend(bytearray(packet[image_start_pos:]))

                        image_frame_len = image_frame_len - len(packet[image_start_pos:])
                        packet = ""
                        print(image_frame_len, " image bytes in next packet")

                    else:
                        # Sometimes multiple image frames coincide in the same packet
                        framebuffer.extend(bytearray(packet[image_start_pos:image_frame_end]))

                        image_frame_len = 0
                        print ("End of frame:", packet[image_frame_end - 2 : image_frame_end + 4].hex())
                        if packet[image_frame_end - 2 : image_frame_end] == JFIF_EOI:
                            print("Found end of frame 1")
#                            frame.write(framebuffer)
#                            frame.close()
                            frame_queue.put(framebuffer)
                            framebuffer = None
#                            frame = None

                        # Skip all packet consumed in this packet
                        packet = packet[image_frame_end:]
                else:
                    # Skip non image ctrl frame for now
                    packet = packet[ctrl_header_end + 1:]

            else:
                # Continuation of a previous image
                # Sometimes an image frame overlaps multiple packets
                if image_frame_len > len(packet):
                    # frame.write(packet)
                    framebuffer.extend(bytearray(packet))
                    image_frame_len = image_frame_len - len(packet)
                    packet = ""
                else:
                    # frame.write(packet[:image_frame_len])
                    framebuffer.extend(bytearray(packet[:image_frame_len]))

                    if packet[image_frame_len - 2:image_frame_len] == JFIF_EOI:
                        print("Found end of frame 2")
#                        frame.write(framebuffer)
#                        frame.close()
                        frame_queue.put(framebuffer)
                        framebuffer = None
#                        frame = None

                    packet = packet[image_frame_len:]
                    image_frame_len = 0

frame_queue = queue.Queue()

recv_thread = threading.Thread(target=recv_thread, args=(frame_queue, ))
recv_thread.start()

while True:
    frame = frame_queue.get()
#    print("Got frame ", frame)
    nparr = numpy.frombuffer(frame, numpy.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    cv2.imshow('window', image)
    cv2.waitKey(1)
