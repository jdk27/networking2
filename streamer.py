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
        self.corrupted_count = 0

    def send(self, data_bytes: bytes):
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        # length check should be dif bc must make space for header
        checksum = self.calculate_checksum(data_bytes)
        header = str(self.expected_num).encode('utf-8') + \
            b'C'+checksum.encode('utf-8')+b'\r\n\r\n'
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
        checksum = get_checksum(data).decode('utf-8')
        print(checksum)
        calculated_checksum = self.calculate_checksum(get_payload(data))
        print(calculated_checksum)
        if checksum != self.calculate_checksum(get_payload(data)):
            print('corrupted segment')
            self.corrupted_count += 1
            return b''
        # if not expected data, add it to the buffer and return nothing
        if seq_num != self.expected_num:
            self.rec_buf[seq_num] = data
            return b''

        # if expected data, check buffer for contiguous segments and return total contiguous payload
        self.expected_num += len(data)
        application_data = get_payload(data)
        while self.expected_num in self.rec_buf:
            application_data += get_payload(self.rec_buf[self.expected_num])
            new_expected_num = self.expected_num + \
                len(self.rec_buf[self.expected_num])
            self.rec_buf.pop(self.expected_num)
            self.expected_num = new_expected_num
        return application_data

    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
        print('corrupted segments: ' + str(self.corrupted_count))

    def calculate_checksum(self, msg):
        msg = msg.decode('utf-8')
        s = 0       # Binary Sum
        # loop taking 2 characters at a time
        for i in range(0, len(msg), 2):
            if (i+1) < len(msg):
                a = ord(msg[i])
                b = ord(msg[i+1])
                s = s + (a+(b << 8))
            elif (i+1) == len(msg):
                s += ord(msg[i])
            else:
                raise "Something Wrong here"
        # One's Complement
        s = s + (s >> 16)
        s = ~s & 0xffff
        return str(s)


def get_seq_num(data: bytes):
    num = data.decode('utf-8')
    return int(num[:num.find('C')])


def get_payload(data: bytes):
    data = data.decode('utf-8')
    return data[data.find('\r\n\r\n')+len('\r\n\r\n'):].encode('utf-8')


def get_checksum(data: bytes):
    data = data.decode('utf-8')
    return data[data.find('C')+1:data.find('\r\n\r\n')].encode('utf-8')
