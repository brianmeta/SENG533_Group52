import logging
import time
from random import randint
from locust import HttpUser, task

logging.getLogger().setLevel(logging.INFO)

# Small delay between requests to simulate real user behavior
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
        
        self.visit_profile()
        time.sleep(REQUEST_DELAY)
        
        self.logout()
        logging.info("Completed user.")

    def visit_home(self):
        res = self.client.get('/')
        if res.ok:
            logging.info("Loaded landing page.")
        else:
            logging.error(f"Could not load landing page: {res.status_code}")

    def login(self):
        # First load the login page
        res = self.client.get('/login')
        if not res.ok:
            logging.error(f"Could not load login page: {res.status_code}")
            return
        
        logging.info("Loaded login page.")
        
        # Generate random user ID and attempt login
        user = randint(1, 99)
        login_res = self.client.post("/loginAction", 
                                     params={"username": user, "password": "password"})
        
        if login_res.ok:
            logging.info(f"Login with username: {user}")
        else:
            logging.error(f"Could not login with username: {user} - status: {login_res.status_code}")

    def browse(self):
        """Browse random categories and add products to cart"""
        num_items = randint(2, 5)
        
        for _ in range(1, num_items):
            category_id = randint(2, 6)
            page = randint(1, 5)
            
            cat_res = self.client.get("/category", 
                                      params={"page": page, "category": category_id})
            
            if not cat_res.ok:
                logging.error(f"Could not visit category {category_id} on page {page} - status {cat_res.status_code}")
                continue
            
            logging.info(f"Visited category {category_id} on page {page}")
            
            # Visit a product from this category
            product_id = randint(7, 506)
            prod_res = self.client.get("/product", params={"id": product_id})
            
            if not prod_res.ok:
                logging.error(f"Could not visit product {product_id} - status {prod_res.status_code}")
                continue
            
            logging.info(f"Visited product with id {product_id}.")
            
            # Try adding to cart
            cart_res = self.client.post("/cartAction", 
                                        params={"addToCart": "", "productid": product_id})
            
            if cart_res.ok:
                logging.info(f"Added product {product_id} to cart.")
            else:
                logging.error(f"Could not put product {product_id} in cart - status {cart_res.status_code}")

    def visit_profile(self):
        profile_res = self.client.get("/profile")
        
        if profile_res.ok:
            logging.info("Visited profile page.")
        else:
            logging.error("Could not visit profile page.")

    def logout(self):
        logout_res = self.client.post("/loginAction", params={"logout": ""})
        
        if logout_res.ok:
            logging.info("Successful logout.")
        else:
            logging.error(f"Could not log out - status: {logout_res.status_code}")





