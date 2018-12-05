import socket

# This is an example of a UDP client - it creates
# a socket and sends data through it

# create the UDP socket
UDPSock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

data = " jasjlsdfjk sdkldfkjlsd jlksfjklsd\n"

# Simply set up a target address and port ...
addr = ("localhost",int(raw_input("PORTA: ")))
# ... and send data out to it!
UDPSock.sendto(data,addr)
