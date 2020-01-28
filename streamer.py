# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY


class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.seq_num = 0
        self.rec_buf = []

    def send(self, data_bytes: bytes):
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # length check should be dif bc must make space for header
        header = bytes(b"".join([bytes(self.seq_num), b'\r\n\r\n']))
        print('Header: ' + str(header))
        payload = data_bytes
        if len(data_bytes) > 1472-len(header):
            payload = data_bytes[:1472-len(header)]
            remainder = data_bytes[1472:]
            data_bytes = data_bytes[:1472]
            packet = b"".join([header, payload])
            self.seq_num += len(packet)
            # for now I'm just sending the raw application-level data in one UDP payload
            self.socket.sendto(packet, (self.dst_ip, self.dst_port))
            self.send(remainder)
        else:
            self.send(b"".join([header, payload]))

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        # get the data
        # check its sequence number
        # if there is a gap, do something
        # if there is no gap, do something else
        #

        # this sample code just calls the recvfrom method on the LossySocket
        data, addr = self.socket.recvfrom()
        # For now, I'll just pass the full UDP payload to the app
        return data
