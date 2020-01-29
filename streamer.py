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
        self.expected_num = 0
        self.rec_buf = {}

    def send(self, data_bytes: bytes):
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # length check should be dif bc must make space for header
        print('sequence number: ' + str(self.expected_num))
        header = str(self.expected_num).encode('utf-8')+b'\r\n\r\n'
        if len(data_bytes) + len(header) > 1472:
            payload = data_bytes[:1472-len(header)]
            self.socket.sendto(header+payload, (self.dst_ip, self.dst_port))
            self.expected_num += 1472
            self.send(data_bytes[1472-len(header):])
        else:
            self.socket.sendto(header+data_bytes, (self.dst_ip, self.dst_port))
            self.expected_num += len(header)+len(data_bytes)

    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!

        data, addr = self.socket.recvfrom()
        seq_num = get_seq_num(data)
        # keep retrieving data until the expected sequence num comes
        while seq_num != self.expected_num:
            self.rec_buf[seq_num] = data
            data, addr = self.socket.recvfrom()
            seq_num = get_seq_num(data)
            # if incoming data doesn't have sequence num, add it to the buffer
        # increase the expected sequence num once the packet has come in
        self.expected_num += len(data)
        application_data = get_payload(data)
        while self.expected_num in self.rec_buf:
            application_data += get_payload(self.rec_buf[self.expected_num])
            new_expected_num = self.expected_num + \
                len(self.rec_buf[self.expected_num])
            self.rec_buf.pop(self.expected_num)
            self.expected_num = new_expected_num
        return application_data


def get_seq_num(data: bytes):
    num = data.decode('utf-8')
    return int(num[:num.find('\r\n\r\n')])


def get_payload(data: bytes):
    data = data.decode('utf-8')
    return data[data.find('\r\n\r\n')+len('\r\n\r\n'):].encode('utf-8')
