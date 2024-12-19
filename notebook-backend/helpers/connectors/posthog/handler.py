from helpers.supabase.connector_credentials import create_connector_credentials

class PostHogHandler:
    def __init__(self, user_id: str, notebook_id: str, api_key: str, base_url: str):
        self.user_id = user_id
        self.notebook_id = notebook_id
        self.api_key = api_key
        self.base_url = base_url
        self.credentials = {
            "api_key": self.api_key,
            "base_url": self.base_url
        }

    def inject_posthog_in_notebook(self):
        code = f"""
        from connectors.services.posthog.posthog_service import PostHogService
        from IPython import get_ipython
        # Initialize PostHog service
        posthog_service = PostHogService({self.credentials})
        # Get IPython instance and inject into namespace
        ipython = get_ipython()
        ipython.user_ns['posthog_service'] = posthog_service
        ipython.user_ns['posthog_client'] = posthog_service.client
        ipython.user_ns['posthog_adapter'] = posthog_service.adapter
        """
        return code
    
    def setup_posthog_in_notebook(self):
        # Task 1: Insert PostHog credentials into the database
  

        response = create_connector_credentials(
            user_id=self.user_id, 
            notebook_id=self.notebook_id, 
            connector_type='posthog', 
            credentials=self.credentials
        )

        if response['statusCode'] != 200:
            return {
                'success': False,
                'body': response['body'],
                'message': response['message']
            }
        
        # Task 2: Inject PostHog into the notebook
        code = self.inject_posthog_in_notebook()
        
        return {
            'success': True,
            'body': code,
            'message': 'PostHog inserted into database'
        }