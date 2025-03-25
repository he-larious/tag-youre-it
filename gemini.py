import google.generativeai as genai

# Generate response to prompt
def get_gemini_completion(prompt, model_name="gemini-2.0-flash", max_tokens=200, temperature=0.2, top_p=1, top_k=32):
    # Initialize a generative model
    model = genai.GenerativeModel(model_name)

    # Configure the model with your desired parameters
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k
    )

    # Generate a response
    response = model.generate_content(prompt, generation_config=generation_config)

    return response.text.strip() if response.text else "No response received"


def extract_relations_gemini(gemini_api_key):
    genai.configure(gemini_api_key)

    prompt_text = '''
    
    '''

    response_text = get_gemini_completion(prompt_text)