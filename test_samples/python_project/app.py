from config import settings
from constants import DEFAULT_PAGE_SIZE
from models import User, Product, Order
from services import AuthService, UserService, OrderService
from routes import AuthRouter, UserRouter, OrderRouter
from database import init_db, close_db
from utils import Paginator


class Application:
    def __init__(self):
        init_db()
        self.auth_service  = AuthService()
        self.user_service  = UserService(self.auth_service)
        self.order_service = OrderService()
        self.auth_routes   = AuthRouter(self.user_service, self.auth_service)
        self.user_routes   = UserRouter(self.user_service, self.auth_service)
        self.order_routes  = OrderRouter(self.order_service, self.auth_service)

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        print(f"Starting on {host}:{port}  debug={settings.debug}  page_size={DEFAULT_PAGE_SIZE}")

    def shutdown(self) -> None:
        close_db()
        print("Shutdown complete")


if __name__ == "__main__":
    app = Application()
    app.run()
