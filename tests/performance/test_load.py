# test_load.py - Tests de charge et performance

import pytest
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

@pytest.mark.slow
class TestPerformance:
    """Tests de performance et charge."""
    
    @pytest.fixture
    def base_url(self):
        """URL de base pour les tests de performance."""
        return 'http://localhost:5000'
    
    async def make_request(self, session, url, method='GET', data=None):
        """Faire une requête HTTP asynchrone."""
        start_time = time.time()
        try:
            if method == 'GET':
                async with session.get(url) as response:
                    await response.text()
                    return {
                        'status': response.status,
                        'time': time.time() - start_time,
                        'success': response.status < 400
                    }
            elif method == 'POST':
                async with session.post(url, json=data) as response:
                    await response.text()
                    return {
                        'status': response.status,
                        'time': time.time() - start_time,
                        'success': response.status < 400
                    }
        except Exception as e:
            return {
                'status': 0,
                'time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    @pytest.mark.asyncio
    async def test_homepage_load_time(self, base_url):
        """Test du temps de chargement de la page d'accueil."""
        async with aiohttp.ClientSession() as session:
            result = await self.make_request(session, base_url)
            
            assert result['success'], f"Homepage failed to load: {result.get('error', 'Unknown error')}"
            assert result['time'] < 2.0, f"Homepage load time too slow: {result['time']:.2f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_homepage_requests(self, base_url):
        """Test de requêtes concurrentes sur la page d'accueil."""
        concurrent_requests = 50
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.make_request(session, base_url)
                for _ in range(concurrent_requests)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Analyser les résultats
            successful_requests = [r for r in results if r['success']]
            failed_requests = [r for r in results if not r['success']]
            
            success_rate = len(successful_requests) / len(results) * 100
            average_time = statistics.mean([r['time'] for r in successful_requests])
            max_time = max([r['time'] for r in successful_requests])
            
            print(f"\nConcurrent requests results:")
            print(f"Success rate: {success_rate:.1f}%")
            print(f"Average response time: {average_time:.3f}s")
            print(f"Max response time: {max_time:.3f}s")
            print(f"Failed requests: {len(failed_requests)}")
            
            # Assertions
            assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
            assert average_time < 1.0, f"Average response time too slow: {average_time:.3f}s"
            assert max_time < 5.0, f"Max response time too slow: {max_time:.3f}s"
    
    @pytest.mark.asyncio
    async def test_api_performance(self, base_url):
        """Test de performance des APIs."""
        endpoints = [
            '/api/autocomplete?q=Paris',
            '/health',
            '/api/status'
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                url = f"{base_url}{endpoint}"
                result = await self.make_request(session, url)
                
                print(f"\nAPI {endpoint}:")
                print(f"Status: {result['status']}")
                print(f"Time: {result['time']:.3f}s")
                print(f"Success: {result['success']}")
                
                if endpoint != '/api/autocomplete?q=Paris':  # Autocomplete peut être plus lent
                    assert result['time'] < 0.5, f"API {endpoint} too slow: {result['time']:.3f}s"
                assert result['success'], f"API {endpoint} failed"
    
    def test_database_query_performance(self, db_session, sample_user):
        """Test de performance des requêtes base de données."""
        from backend.models import RouteHistory, SavedRoute, RouteAnalytics
        
        # Créer des données de test
        for i in range(100):
            history = RouteHistory(
                user_id=sample_user.id,
                origin_address=f'Origin {i}',
                origin_lat=48.8566 + i * 0.001,
                origin_lng=2.3522 + i * 0.001,
                destination_address=f'Destination {i}',
                destination_lat=45.7640 + i * 0.001,
                destination_lng=4.8357 + i * 0.001,
                travel_time_seconds=3600,
                distance_meters=50000,
                optimization_score=8.0
            )
            db_session.add(history)
        db_session.commit()
        
        # Test des requêtes
        queries = [
            lambda: RouteHistory.query.filter_by(user_id=sample_user.id).all(),
            lambda: RouteAnalytics.get_user_analytics(sample_user.id),
            lambda: RouteAnalytics.get_weekly_stats(sample_user.id),
            lambda: SavedRoute.query.filter_by(user_id=sample_user.id).all()
        ]
        
        for i, query_func in enumerate(queries):
            start_time = time.time()
            result = query_func()
            query_time = time.time() - start_time
            
            print(f"\nQuery {i+1} time: {query_time:.3f}s")
            assert query_time < 1.0, f"Query {i+1} too slow: {query_time:.3f}s"
    
    def test_memory_usage(self, app):
        """Test d'utilisation mémoire."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Mesure initiale
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulation de charge
        with app.test_client() as client:
            for _ in range(100):
                client.get('/')
                client.get('/search')
                client.get('/about')
        
        # Mesure finale
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory usage:")
        print(f"Initial: {initial_memory:.1f} MB")
        print(f"Final: {final_memory:.1f} MB")
        print(f"Increase: {memory_increase:.1f} MB")
        
        # Vérifier qu'il n'y a pas de fuite mémoire excessive
        assert memory_increase < 50, f"Memory increase too high: {memory_increase:.1f} MB"

@pytest.mark.slow
class TestScalability:
    """Tests de scalabilité."""
    
    def test_database_connection_pool(self, app):
        """Test du pool de connexions base de données."""
        from backend.models import db
        
        # Simuler plusieurs connexions simultanées
        def make_db_query():
            with app.app_context():
                return db.session.execute('SELECT 1').scalar()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_db_query) for _ in range(50)]
            results = [future.result() for future in futures]
        
        # Vérifier que toutes les requêtes ont réussi
        assert all(result == 1 for result in results)
    
    def test_cache_efficiency(self, app, mock_redis):
        """Test d'efficacité du cache."""
        from backend.services.cache_service import CacheService
        
        cache = CacheService()
        
        # Test de mise en cache
        test_data = {'test': 'data', 'number': 42}
        cache.set('test_key', test_data, ttl=300)
        
        # Test de récupération
        cached_data = cache.get('test_key')
        assert cached_data == test_data
        
        # Test de performance avec cache
        start_time = time.time()
        for _ in range(100):
            cache.get('test_key')
        cache_time = time.time() - start_time
        
        print(f"Cache access time for 100 operations: {cache_time:.3f}s")
        assert cache_time < 0.1, f"Cache too slow: {cache_time:.3f}s"