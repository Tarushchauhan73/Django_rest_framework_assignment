from wsgiref.simple_server import make_server

from app.config import DEFAULT_HOST, DEFAULT_PORT
from app.server import application, setup_application


if __name__ == "__main__":
    setup_application()
    server = make_server(DEFAULT_HOST, DEFAULT_PORT, application)
    print(f"Server running on http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    server.serve_forever()
