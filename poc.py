import socket
import threading
import time

TCP_IP = '192.168.1.1'
#TCP_IP = 'Barnard.familjen.com'
TCP_PORT = 80
BUFFER_SIZE = 16384

JFIF_SOI = b'\xff\xd8'
JFIF_EOI = b'\xff\xd9'

FRAME_CONTROL_HEADER = b'\x05\x33\x8b\x11'

FRAME_HEADER_BASE_LENGTH = 10

FRAME_COMMAND_POS = 4
FRAME_HEADER_LENGTH_POS = 6
FRAME_IMAGE_LENGTH_MSB_POS = 7
FRAME_IMAGE_LENGTH_LSB_POS = 8

FRAME_COMMAND_ENABLE_STREAM = 0x0e
FRAME_COMMAND_IMAGE = 0x25

SEARCH_FOR_HEADER = 1
RECEIVING_IMAGE = 2
FIND_SOI = 1
FIND_EOI = 2

def recv_thread(sock):
    print("Starting receive thread")
    frame_state = SEARCH_FOR_HEADER
    frame = None
    image_frame_len = 0

    while True:
        packet = sock.recv(BUFFER_SIZE)
        print ("Received packet of length: ", len(packet))

        while len(packet) > 0:
            if image_frame_len == 0:
                ctrl_header_pos = packet.find(FRAME_CONTROL_HEADER)

                if ctrl_header_pos == -1:
                    break;

                ctrl_header_end = packet[ctrl_header_pos + FRAME_HEADER_LENGTH_POS] + 9
                ctrl_header = packet[ctrl_header_pos:ctrl_header_end]
                print("Ctrl header" , ctrl_header.hex(), " end: ", ctrl_header_end)

                frame_command = ctrl_header[FRAME_COMMAND_POS]
                if frame_command == FRAME_COMMAND_IMAGE:
                    print("Frame image command")
                    frame_state = RECEIVING_IMAGE

                    # Relative packet
                    image_start_pos = ctrl_header_pos + ctrl_header[FRAME_HEADER_LENGTH_POS] + 10
                    print("Frame image length: ", ctrl_header[FRAME_IMAGE_LENGTH_MSB_POS:FRAME_IMAGE_LENGTH_LSB_POS + 1])
                    image_frame_len = int.from_bytes(ctrl_header[FRAME_IMAGE_LENGTH_MSB_POS:FRAME_IMAGE_LENGTH_LSB_POS + 1], "big")
                    image_frame_end = image_start_pos + image_frame_len

                    if image_frame_len == 0:
                        print("End of image frame")
                        frame.write(packet[10:])
                        frame.close()
                        frame.close()
                        packet = ""
                        continue

                    print("image starts at: ", image_start_pos, " image frame len ", image_frame_len, " ends ", image_frame_end, " first bytes ", packet[image_start_pos:image_start_pos + 2])
                    if packet[image_start_pos:image_start_pos + 2] == JFIF_SOI:
                        ts = time.time()
                        filename = "frame_" + str(ts) + ".jpg"
                        frame = open(filename, "wb")
                    elif frame == None:
                        print("Did not find JFIF SOF at start of new image")
                        quit(-1)

                    # Sometimes image frame overlaps multiple network packets
                    print ("image frame length: " , image_frame_len, " rest of packet: ", len(packet[image_start_pos:]))
                    if image_frame_len > len(packet[image_start_pos:]):
                        print("Image frame overlaps packet")
                        frame.write(packet[image_start_pos:])
                        image_frame_len = image_frame_len - len(packet[image_start_pos:])
                        packet = ""
                        print(image_frame_len, " image bytes in next packet")

                    else:
                        # Sometimes multiple image frames coincide in the same packet
                        frame.write(packet[image_start_pos:image_frame_end])
                        image_frame_len = 0
                        print ("End of frame: ", packet[image_frame_end - 2 : image_frame_end + 4].hex())
                        if packet[image_frame_end - 2 : image_frame_end] == JFIF_EOI:
                            print("Found end of frame")
                            frame.close()
                            frame = None

                        # Skip all packet consumed in this packet
                        packet = packet[image_frame_end:]
                        print("Start of next packet: ", packet[:2].hex())
                else:
                    # Skip non image ctrl frame for now
                    packet = packet[ctrl_header_end + 1:]

            elif frame != None:
                # Continuation of a previous image
                # Sometimes an image frame overlaps multiple packets
                if image_frame_len > len(packet):
                    frame.write(packet)
                    image_frame_len = image_frame_len - len(packet)
                    packet = ""
                else:
                    frame.write(packet[:image_frame_len])
                    if packet[image_frame_len - 2:image_frame_len] == JFIF_EOI:
                        print("Found end of frame")
                        frame.close()
                        frame = None

                    packet = packet[image_frame_len:]
                    image_frame_len = 0
                    print("Start of next packet: ", packet[:2].hex())


# This is the smallest message we can send to get images flowing
MSG_6 = b'\x05\x33\x8b\x11\x0e\x00\x04\x00\x00\x00\x00\x00\x00\x00'

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TCP_IP, TCP_PORT))

recv_thread = threading.Thread(target=recv_thread, args=(sock,))
recv_thread.start()

sock.send(MSG_6)
