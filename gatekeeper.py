import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from functools import partial

hostName = "0.0.0.0"
serverPort = 8080

CONFIG_PATH = "gatekeeper.conf"


class ConfigReader:
    STATUS_READ_SUCCESSFULLY = 0
    STATUS_NOT_FOUND = 1
    STATUS_EMPTY = 2
    STATUS_CAN_NOT_CREATE = 3

    def __init__(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                self.__ip = f.readline()
                if self.__ip is None or self.__ip == '':
                    self.__ip = None
                    self.__status = ConfigReader.STATUS_EMPTY
                else:
                    self.__status = ConfigReader.STATUS_READ_SUCCESSFULLY
        except FileNotFoundError as e:
            self.__ip = None
            try:
                with open(CONFIG_PATH, 'w') as f:
                    f.write('')
                self.__status = ConfigReader.STATUS_NOT_FOUND
            except PermissionError:
                self.__status = ConfigReader.STATUS_CAN_NOT_CREATE

    def status(self):
        return self.__status


class MyServer(BaseHTTPRequestHandler):
    HTML_DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    HTML_META = '<meta http-equiv="Content-Type" content="text/html;charset=utf-8">'
    CSS = '''
    body { font-family: sans-serif; margin: auto; max-width: 600pt; padding: 20pt; }
    h1 { text-size: 200%; }
    '''

    def __init__(self, request: bytes, client_address: tuple[str, int], server: socketserver.BaseServer, *args,
                 **kwargs):
        self.__configReader = ConfigReader()
        super().__init__(request, client_address, server)

    def get_no_permission_page(self):
        response = f'''{self.HTML_DOCTYPE}
        <html>
            <head>
                {self.HTML_META}
                <title>The Gatekeeper</title>
                <style>{self.CSS}</style>
            </head>
            <body>
                <h1>Gatekeeper can not proceed!</h1>
                <p>The Gatekeeper has no writing access to its configuration file: <code>{CONFIG_PATH}</code>. Please stop the server and grant it the proper permissions</p>
            </body>
        </html>
        '''

        return response

    def get_welcome_page(self):
        server_ip = self.connection.getsockname()[0]
        response = f'''{self.HTML_DOCTYPE}
        <html>
            <head>
                {self.HTML_META}
                <title>The Gatekeeper</title>
                <style>{self.CSS}</style>
            </head>
            <body>
                <h1>Welcome to the Gatekeeper!</h1>
                <p>The server can not find its configuration file at <code>{CONFIG_PATH}</code> or the file is empty. We have to configure the Gatekeeper.</p>
                <p>The server was reached at IP <code>{server_ip}</code>. May we assume this IP address to be the client network address? If not, open the Gatekeeper page from the client network.</p>
            </body>
        </html>
        '''
        return response

    def do_GET(self):
        if self.__configReader.status() == ConfigReader.STATUS_CAN_NOT_CREATE:
            page = self.get_no_permission_page()
        elif self.__configReader.status() == ConfigReader.STATUS_NOT_FOUND or self.__configReader.status() == ConfigReader.STATUS_EMPTY:
            page = self.get_welcome_page()
        else:
            page = "Done"

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(page, "utf-8"))


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")