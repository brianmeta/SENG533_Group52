import logging
import time
from random import randint
from locust import HttpUser, task

logging.getLogger().setLevel(logging.INFO)

REQUEST_DELAY = 0.025


class UserBehavior(HttpUser):
    
    @task
    def load(self):
        logging.info("Starting user.")
        self.visit_home()
        time.sleep(REQUEST_DELAY)
        self.login()
        time.sleep(REQUEST_DELAY)
        self.browse()
        time.sleep(REQUEST_DELAY)
        self.buy()
        time.sleep(REQUEST_DELAY)
        self.visit_profile()
        time.sleep(REQUEST_DELAY)
        self.logout()
        logging.info("Completed user.")
    
    def visit_home(self):
        r = self.client.get('/')
        if r.ok:
            logging.info("Loaded landing page.")
        else:
            logging.error(f"Could not load landing page: {r.status_code}")
    
    def login(self):
        r = self.client.get('/login')
        if not r.ok:
            logging.error(f"Could not load login page: {r.status_code}")
            return
        
        logging.info("Loaded login page.")
        
        user = randint(1, 99)
        r = self.client.post("/loginAction", params={"username": user, "password": "password"})
        if r.ok:
            logging.info(f"Login with username: {user}")
        else:
            logging.error(f"Could not login with username: {user} - status: {r.status_code}")
    
    def browse(self):
        for _ in range(1, randint(2, 5)):
            cat_id = randint(2, 6)
            page = randint(1, 5)
            
            r = self.client.get("/category", params={"page": page, "category": cat_id})
            if not r.ok:
                logging.error(f"Could not visit category {cat_id} on page {page} - status {r.status_code}")
                continue
            
            logging.info(f"Visited category {cat_id} on page {page}")
            
            prod_id = randint(7, 506)
            r = self.client.get("/product", params={"id": prod_id})
            if r.ok:
                logging.info(f"Visited product with id {prod_id}.")
            else:
                logging.error(f"Could not visit product {prod_id} - status {r.status_code}")
    
    def buy(self) -> None:
        user_data = {
            "firstname": "User",
            "lastname": "User",
            "adress1": "Road",
            "adress2": "City",
            "cardtype": "volvo",
            "cardnumber": "314159265359",
            "expirydate": "12/2050",
            "confirm": "Confirm"
        }
        buy_request = self.client.post("/cartAction", params=user_data)
        if buy_request.ok:
            logging.info("Bought products.")
        else:
            logging.error("Could not buy products.")
    
    def visit_profile(self):
        r = self.client.get("/profile")
        if r.ok:
            logging.info("Visited profile page.")
        else:
            logging.error("Could not visit profile page.")
    
    def logout(self):
        r = self.client.post("/loginAction", params={"logout": ""})
        if r.ok:
            logging.info("Successful logout.")
        else:
            logging.error(f"Could not log out: status: {r.status_code}")
