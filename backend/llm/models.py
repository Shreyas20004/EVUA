import ollama

def get_available_models():
    """
    Get the list of available models from Ollama.
    
    Returns:
        list: A list of available model names
    """
    try:
        response = ollama.list()
        # Extract model names from the ListResponse object
        model_names = [model.model for model in response.models]
        return model_names
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []
