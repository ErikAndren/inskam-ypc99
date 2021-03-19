import socket
import threading
import time

TCP_IP = '192.168.1.1'
#TCP_IP = 'Barnard.familjen.com'
TCP_PORT = 80
BUFFER_SIZE = 16384

JFIF_SOI = b'\xff\xd8'
JFIF_EOI = b'\xff\xd9'

FIND_SOI = 1
FIND_EOI = 2

def recv_thread(sock):
    print("Starting receive thread")
    frame_state = FIND_SOI
    frame = None

    while True:
        data = sock.recv(BUFFER_SIZE)
        #print("Got ", data.hex(), " or ", data)

        while True:
            soi_pos = -1
            eoi_pos = -1

            if frame_state == FIND_SOI:
                soi_pos = data.find(JFIF_SOI)

                if soi_pos != -1:
                    frame_state = FIND_EOI

                else:
                    # Could not find any more SOI in this packet, discard rest of packet
                    break

            if frame_state == FIND_EOI:
                eoi_pos = data.find(JFIF_EOI)
                if eoi_pos != -1:
#                    print("Found end of frame")
#                    print(data[eoi_pos:eoi_pos + 2])
#                    quit()

                    # Found end of frame
                    frame_state = FIND_SOI

            # Found a complete frame (soi + eoi)
            if soi_pos != -1 and eoi_pos != -1:
                ts = time.time()
                filename = "frame_" + str(ts) + ".jpg"
                frame = open(filename, "wb")
                frame.write(data[soi_pos:eoi_pos + 2])
                frame.close()

#                print("Found soi and eoi")
#                print(data[soi_pos:eoi_pos + 3])

                # Discard frame from packet
                data = data[eoi_pos + 3:]

            # Found start but not end of frame, treat rest of packet as start of a frame
            elif soi_pos != -1 and eoi_pos == -1:
                ts = time.time()
                filename = "frame_" + str(ts) + ".jpg"
                frame = open(filename, "wb")
                frame.write(data[soi_pos:])

#                print("Found soi")
#                print(data[soi_pos:])

                # Packet handled, wait for next packet
                break

            # Found end of frame, write packet until end of frame
            elif soi_pos == -1 and eoi_pos != -1:
                frame.write(data[:eoi_pos + 2])
                frame.close()

                #print("Found eoi")
                #print(data[:eoi_pos + 2].hex())
                #print(data[eoi_pos:eoi_pos + 2])
                #quit()

                # Discard frame from packet
                data = data[eoi_pos + 3:]

            # Found continuation of frame, write to image and then wait for next packet
            elif frame_state == FIND_EOI and eoi_pos == -1:
#                print("Found middle of frame")
#                print(data)

                frame.write(data)
                break
# 05 33 8b 11 - Some kind of control header
# 05 33 8b 11 06 00 27 00 00 00 00 22 00 00 00
#  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
# 05 33 8b 11 03 00 05 00 00 00 00 ff ff 01 00
#  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
# Byte 5 is command
# 00 = Client Ping?
# 01 = Server Pong?
# 02 = Client Request for something
# 03 = Server Reply
# 05 = Client ?
# 06 = Server Send firmware and voudp
# 09 = Client update time and timezone clock= tz= save=[0, 1], update_tz
# 0A = Server ?
# 0B = Client sends ascii parameters
# 0C = Server ?
# 0D = Server send settings, power, motor, record, disk, zoom
# 0E = Client Start stream
# 0F = Server ?
# 1C = Client ?
# 25 = Server frame
# 2F = Client


# 05 33 8b 11 0f 00 01 00  00 00 00
# Frame 1 - Sop at 0xFA
# 05 33 8b 11 25 00 12 04 00 00 03 00 0f 00 00 01 95 8f 00 00 00 00 00 00 cc 1e 00 00 ff d8
#  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26
# Frame 1 - middle of packet 0x4FA (0x400) = 1024
# 05 33 8b 11 25 00 01 04 00 00 02 51 4d 34 51 4d a6 d1 45 34 d3 68 a2 92 9a 68 a2 99 45 14 53 29

# Frame 2
# 05 33 8b 11 25 00 12 04 00 00 03 00 0f 00 00 01 95 8f 00 00 00 00 00 00 18 1f 00 00 ff d8


MSG_1 = b'\x05\x33\x8b\x11\x00\x00\x00\x00\x00\x00'
MSG_2 = b'\x05\x33\x8b\x11\x02\x00\x12\x00\x00\x00\x06\x41\x44\x10\x18\x01\xf3\xf2\xd8\x01\x43\x74\x4e\x18\x1f\x3b\x03\x5a'
MSG_3 = b'\x05\x33\x8b\x11\x2f\x00\x01\x00\x00\x00\x00\x05\x33\x8b\x11\x05\x00\x00\x00\x00\x00'
MSG_4 = b'\x05\x33\x8b\x11\x0b\x00\xed\x00\x00\x00\x61\x6c\x61\x72\x6d\x00\x64\x69\x73\x6b\x00\x72\x65\x63\x6f\x72\x64\x00\x77\x69\x66\x69\x5f\x73\x69\x67\x6e\x61\x6c\x5f\x6c\x65\x76\x65\x6c\x00\x74\x65\x6d\x70\x65\x72\x61\x74\x75\x72\x65\x00\x6d\x65\x69\x6a\x69\x6e\x67\x5f\x70\x6c\x61\x79\x00\x6d\x65\x69\x6a\x69\x6e\x67\x5f\x6c\x65\x64\x00\x70\x6f\x77\x65\x72\x64\x6f\x77\x6e\x00\x62\x65\x6c\x6c\x00\x61\x72\x6d\x00\x64\x69\x6a\x69\x61\x5f\x73\x74\x61\x74\x75\x73\x00\x64\x69\x6a\x69\x61\x5f\x6d\x75\x74\x65\x00\x64\x69\x6a\x69\x61\x5f\x73\x70\x65\x65\x64\x00\x70\x6f\x77\x65\x72\x00\x65\x77\x69\x67\x5f\x6d\x65\x6c\x6f\x64\x79\x5f\x73\x69\x7a\x65\x00\x65\x77\x69\x67\x5f\x66\x6f\x6f\x64\x00\x65\x77\x69\x67\x5f\x6d\x6f\x74\x6f\x72\x00\x73\x65\x73\x73\x69\x6f\x6e\x73\x00\x64\x69\x73\x6b\x5f\x73\x69\x7a\x65\x00\x6a\x75\x79\x61\x6e\x67\x5f\x73\x74\x61\x74\x75\x73\x00\x77\x6f\x72\x6b\x69\x6e\x67\x5f\x73\x63\x65\x6e\x65\x73\x00\x72\x66\x5f\x63\x68\x61\x6e\x67\x65\x64\x00\x6d\x6f\x74\x6f\x72\x00'
MSG_5 = b'\x05\x33\x8b\x11\x09\x00\x2d\x00\x00\x00\x63\x6c\x6f\x63\x6b\x3d\x31\x36\x31\x35\x38\x32\x30\x35\x38\x39\x00\x74\x7a\x3d\x2d\x33\x36\x30\x30\x00\x73\x61\x76\x65\x3d\x31\x00\x75\x70\x64\x61\x74\x65\x5f\x74\x7a\x3d\x31\x00'
# Likely the only needed message
#0x0e and 0x04 must be set to get data
#MSG_6 = b'\x05\x33\x8b\x11\x0e\x00\x04\x00\x00\x00\x00\x00\x00\x00\x05\x33\x8b\x11\x1c\x00\x02\x00\x00\x00\x03\x01'
# This is the smallest message we can send to get data
MSG_6 = b'\x05\x33\x8b\x11\x0e\x00\x04\x00\x00\x00\x00\x00\x00\x00'

#print(MSG_1)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TCP_IP, TCP_PORT))

recv_thread = threading.Thread(target=recv_thread, args=(sock,))
recv_thread.start()

#sock.send(MSG_1)
#time.sleep(1)
#sock.send(MSG_2)
#time.sleep(1)
#sock.send(MSG_3)
#time.sleep(1)
#sock.send(MSG_4)
#time.sleep(1)
#sock.send(MSG_5)
#time.sleep(1)
sock.send(MSG_6)
