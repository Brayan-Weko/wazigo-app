# test_user_journey.py - Tests end-to-end des parcours utilisateur

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os

@pytest.mark.e2e
class TestUserJourney:
    """Tests end-to-end du parcours utilisateur."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Configuration du driver Selenium."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def base_url(self):
        """URL de base pour les tests."""
        return os.getenv('TEST_BASE_URL', 'http://localhost:5000')
    
    def test_homepage_loads(self, driver, base_url):
        """Test de chargement de la page d'accueil."""
        driver.get(base_url)
        
        # Vérifier le titre
        assert "Smart Route" in driver.title
        
        # Vérifier les éléments principaux
        assert driver.find_element(By.TAG_NAME, "h1")
        assert driver.find_element(By.CLASS_NAME, "btn-primary")
    
    def test_search_page_navigation(self, driver, base_url):
        """Test de navigation vers la page de recherche."""
        driver.get(base_url)
        
        # Cliquer sur le bouton de recherche
        search_button = driver.find_element(By.LINK_TEXT, "Calculer mon itinéraire")
        search_button.click()
        
        # Vérifier la redirection
        WebDriverWait(driver, 10).until(
            EC.url_contains("/search")
        )
        
        # Vérifier les éléments de la page de recherche
        assert driver.find_element(By.ID, "origin")
        assert driver.find_element(By.ID, "destination")
        assert driver.find_element(By.ID, "route-search-form")
    
    def test_route_search_flow(self, driver, base_url):
        """Test du flux de recherche d'itinéraire."""
        driver.get(f"{base_url}/search")
        
        # Remplir le formulaire de recherche
        origin_input = driver.find_element(By.ID, "origin")
        destination_input = driver.find_element(By.ID, "destination")
        
        origin_input.send_keys("Paris, France")
        time.sleep(1)  # Attendre l'autocomplétion
        
        destination_input.send_keys("Lyon, France")
        time.sleep(1)
        
        # Soumettre le formulaire
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Vérifier la redirection vers les résultats
        WebDriverWait(driver, 15).until(
            EC.url_contains("/results")
        )
        
        # Vérifier les éléments de résultats
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "routes-container"))
        )
    
    def test_mobile_responsive(self, driver, base_url):
        """Test de la responsivité mobile."""
        # Simuler un écran mobile
        driver.set_window_size(375, 667)
        driver.get(base_url)
        
        # Vérifier que le menu mobile est présent
        mobile_menu_button = driver.find_element(By.CSS_SELECTOR, ".md\\:hidden button")
        assert mobile_menu_button.is_displayed()
        
        # Tester l'ouverture du menu mobile
        mobile_menu_button.click()
        time.sleep(0.5)
        
        mobile_menu = driver.find_element(By.ID, "mobile-menu")
        assert "hidden" not in mobile_menu.get_attribute("class")
    
    def test_dark_mode_toggle(self, driver, base_url):
        """Test du toggle mode sombre."""
        driver.get(base_url)
        
        # Trouver et cliquer sur le bouton de thème
        theme_button = driver.find_element(By.CSS_SELECTOR, "button[onclick='toggleTheme()']")
        
        # Vérifier l'état initial
        html_element = driver.find_element(By.TAG_NAME, "html")
        initial_classes = html_element.get_attribute("class")
        
        # Toggle le thème
        theme_button.click()
        time.sleep(0.5)
        
        # Vérifier le changement
        new_classes = html_element.get_attribute("class")
        assert initial_classes != new_classes
    
    @pytest.mark.slow
    def test_pwa_installation(self, driver, base_url):
        """Test de l'installation PWA."""
        driver.get(base_url)
        
        # Vérifier la présence du manifest
        manifest_link = driver.find_element(By.CSS_SELECTOR, "link[rel='manifest']")
        assert manifest_link.get_attribute("href")
        
        # Vérifier la présence du service worker
        sw_script = driver.execute_script("""
            return 'serviceWorker' in navigator;
        """)
        assert sw_script is True
    
    def test_accessibility_basics(self, driver, base_url):
        """Test des bases d'accessibilité."""
        driver.get(base_url)
        
        # Vérifier les attributs alt sur les images
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            alt_text = img.get_attribute("alt")
            assert alt_text is not None, f"Image sans attribut alt: {img.get_attribute('src')}"
        
        # Vérifier les labels sur les inputs
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for input_elem in inputs:
            input_type = input_elem.get_attribute("type")
            if input_type in ["text", "email", "password"]:
                # Vérifier la présence d'un label ou aria-label
                input_id = input_elem.get_attribute("id")
                if input_id:
                    try:
                        driver.find_element(By.CSS_SELECTOR, f"label[for='{input_id}']")
                    except:
                        aria_label = input_elem.get_attribute("aria-label")
                        assert aria_label is not None, f"Input sans label: {input_id}"
    
    def test_performance_basics(self, driver, base_url):
        """Test des bases de performance."""
        start_time = time.time()
        driver.get(base_url)
        
        # Attendre que la page soit complètement chargée
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        load_time = time.time() - start_time
        
        # Vérifier que la page se charge en moins de 5 secondes
        assert load_time < 5, f"Page load time too slow: {load_time:.2f}s"
        
        # Vérifier les métriques de performance
        navigation_timing = driver.execute_script("""
            return {
                loadEventEnd: performance.timing.loadEventEnd,
                navigationStart: performance.timing.navigationStart,
                domContentLoaded: performance.timing.domContentLoadedEventEnd
            };
        """)
        
        total_load_time = (navigation_timing['loadEventEnd'] - navigation_timing['navigationStart']) / 1000
        assert total_load_time < 3, f"Total load time too slow: {total_load_time:.2f}s"

@pytest.mark.e2e
@pytest.mark.slow
class TestAuthenticationFlow:
    """Tests du flux d'authentification."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Configuration du driver pour les tests d'auth."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    def test_login_modal_opens(self, driver, base_url):
        """Test d'ouverture de la modale de connexion."""
        driver.get(f"{base_url}/search")
        
        # Tenter d'accéder à une fonctionnalité nécessitant une auth
        login_button = driver.find_element(By.CSS_SELECTOR, "button[onclick='openAuthModal()']")
        login_button.click()
        
        # Vérifier que la modale s'ouvre
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.ID, "auth-modal"))
        )
        
        auth_modal = driver.find_element(By.ID, "auth-modal")
        assert "hidden" not in auth_modal.get_attribute("class")
    
    def test_guest_mode_functionality(self, driver, base_url):
        """Test des fonctionnalités en mode invité."""
        driver.get(f"{base_url}/search")
        
        # Vérifier que la recherche fonctionne sans authentification
        origin_input = driver.find_element(By.ID, "origin")
        destination_input = driver.find_element(By.ID, "destination")
        
        origin_input.send_keys("Paris")
        destination_input.send_keys("Lyon")
        
        # Les champs doivent être remplis même sans auth
        assert origin_input.get_attribute("value") == "Paris"
        assert destination_input.get_attribute("value") == "Lyon"