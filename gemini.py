import random
import time
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


def extract_relations_gemini(gemini_api_key, target_relation, sentences):
    genai.configure(api_key=gemini_api_key)

    relation_requirements = {
        "Schools_Attended": {
            "subj": "PERSON", 
            "obj": "ORGANIZATION",
            "output": '["Jeff Bezos", "Schools_Attended", "Princeton University"]',
            "sentence": "Jeff Bezos, known for his business acumen, attended Princeton University."
        },
        "Work_For": {
            "subj": "PERSON", 
            "obj": "ORGANIZATION",
            "output": '["Alec Radford", "Work_For", "OpenAI"]',
            "sentence": "Alec Radford, an experienced researcher, recently joined OpenAI as a lead scientist."
        },
        "Live_In": {
            "subj": "PERSON", 
            "obj": "LOCATION or CITY or STATE_OR_PROVINCE or COUNTRY",
            "output": '["Mariah Carey", "Live_In", "New York City"]',
            "sentence": "Mariah Carey, a celebrated singer, lives in New York City."
        },
        "Top_Member_Employees": {
            "subj": "ORGANIZATION", 
            "obj": "PERSON",
            "output": '["Nvidia", "Top_Member_Employees", "Jensen Huang"]',
            "sentence": "Nvidia, a leading tech company, counts Jensen Huang among its top executives."
        }
    }


    for sentence in sentences:
        prompt_text = """
        Below is an example of relation extraction for the '{relation}' relationship:
        Example Output: {relation_output}
        Example Sentence: {relation_sentence}
            
        Now, given the following sentence, extract all instances of the '{relation}' relationship. 
        In this task, the subject should be a {subj_type} and the object should be a {obj_type}.
        Return your answer as a list of lists, where each inner list is formatted as ["Subject", "{relation}", "Object"] and all elements are strings.
        If no relation is found, only return an empty list and nothing else.
        Sentence: {sentence}
        """.format(
            relation=target_relation,
            relation_output=relation_requirements[target_relation]["output"],
            relation_sentence=relation_requirements[target_relation]["sentence"],
            subj_type=relation_requirements[target_relation]["subj"],
            obj_type=relation_requirements[target_relation]["obj"],
            sentence=sentence
        )

        retries = 0
        max_retries = 5
        initial_delay = 2  # start with a 2-second delay instead of 1
        delay = initial_delay
        max_delay = 30  # cap the delay to 30 seconds
        
        while True:
            try:
                response_text = get_gemini_completion(prompt_text)
                break  # Request succeeded, exit the retry loop
            except Exception as e:
                if retries < max_retries:
                    print(f"Error encountered: {e}. Retrying after {delay} seconds...")
                    time.sleep(delay + random.uniform(0, 1))  # add random jitter
                    retries += 1
                    delay = min(delay * 2, max_delay)  # exponential backoff with a max cap
                else:
                    print("Max retries reached. Skipping this sentence.")
                    response_text = ""
                    break

        print("Sentence: ", sentence)
        print("Output: ", response_text)

        # Add a short pause between successful requests to reduce load
        time.sleep(2)