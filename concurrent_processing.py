from concurrent.futures import ThreadPoolExecutor


class concurrent_result:
    def __init__(self, max_workers: int):
        self.max_workers = max_workers

    def get_urls(self, func, queries, *args, **kwargs):
        data = args[0]
        with ThreadPoolExecutor(max_workers=12) as executor:
            print(queries)
            results = executor.map(func, queries)

        # Collect results as they complete
        for result in results:
            data.extend(result)
