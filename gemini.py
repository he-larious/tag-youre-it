import json
import random
import time
import google.generativeai as genai

relation_requirements = {
    "Schools_Attended": {
        "subj": "PERSON", 
        "obj": "SCHOOL",
        "output": '["Jeff Bezos", "Schools_Attended", "Princeton University"]',
        "sentence": "Jeff Bezos, known for his business acumen, attended Princeton University.",
    },
    "Work_For": {
        "subj": "PERSON", 
        "obj": "COMPANY",
        "output": '["Alec Radford", "Work_For", "OpenAI"]',
        "sentence": "Alec Radford, an experienced researcher, recently joined OpenAI as a lead scientist.",
    },
    "Live_In": {
        "subj": "PERSON", 
        "obj": "LOCATION",
        "output": '["Mariah Carey", "Live_In", "New York City"]',
        "sentence": "Mariah Carey, a celebrated singer, lives in New York City.",
    },
    "Top_Member_Employees": {
        "subj": "COMPANY", 
        "obj": "PERSON",
        "output": '["Nvidia", "Top_Member_Employees", "Jensen Huang"]',
        "sentence": "Nvidia, a leading tech company, counts Jensen Huang among its top executives.",
    }
}


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


def extract_relations_gemini(gemini_api_key, target_relation, sentence, results, num_extracted_tuples, num_extracted_sentences):
    genai.configure(api_key=gemini_api_key)

    prompt_text = """
    Below is an example of relation extraction for the '{relation}' relationship:
    Example Output: {relation_output}
    Example Sentence: {relation_sentence}
            
    Now, given the following sentence, extract all instances of the '{relation}' relationship. 
    Return your answer as a list of lists, where each inner array is formatted as ["{subj_type}", "{relation}", "{obj_type}"].
    If no relation is found, return an empty array [].
    Do not include any additional text or markdown formatting.
    Sentence: {sentence}
    """.format(
        relation=target_relation,
        relation_output=relation_requirements[target_relation]["output"],
        relation_sentence=relation_requirements[target_relation]["sentence"],
        subj_type=relation_requirements[target_relation]["subj"],
        obj_type=relation_requirements[target_relation]["obj"],
        sentence=sentence
    )

    # If we don't get a successful response, try again
    retries = 0
    max_retries = 5

    # To avoid resource exhausted errors
    initial_delay = 2  # Start with a 2 second delay
    delay = initial_delay
    max_delay = 30  # Cap the delay to 30 seconds
        
    while True:
        try:
            response_text = get_gemini_completion(prompt_text)
            break  # Request succeeded, exit the retry loop
        except Exception as e:
            if retries < max_retries:
                #print(f"Error encountered: {e}. Retrying after {delay} seconds...")
                time.sleep(delay + random.uniform(0, 1))  # Add jitter
                retries += 1
                delay = min(delay * 2, max_delay)  # Exponential backoff with a max cap
            else:
                #print("Max retries reached. Skipping this sentence.")
                response_text = ""
                break

    # print("Sentence: ", sentence)
    # print("Output: ", response_text)

    num_extracted_tuples, num_extracted_sentences = parse_response_text(sentence, response_text, results, num_extracted_tuples, num_extracted_sentences, target_relation)

    # Add a short pause between successful requests to reduce load
    time.sleep(3)

    return num_extracted_tuples, num_extracted_sentences


def parse_response_text(sentence, response_text, results, num_extracted_tuples, num_extracted_sentences, target_relation):
    # Clean the response text in case Gemini doesn't return a list of lists in the right form
    last_index = response_text.rfind(']')

    if last_index == len(response_text) - 1:
        cleaned_text = response_text
    else:
        cleaned_text = response_text[:last_index+1]
        cleaned_text += ']'

    try:
        parsed_relations = json.loads(cleaned_text)
            
        # Verify parsed result is a list
        if isinstance(parsed_relations, list):
            if len(parsed_relations) != 0:
                num_extracted_sentences += 1
            
            for relation in parsed_relations:
                # Ensure the relation is a list with exactly three items
                if isinstance(relation, list) and len(relation) == 3:
                    num_extracted_tuples += 1

                    print("\n\t\t=== Extracted Relation ===")
                    print("\t\tSentence: ", sentence)
                    print(f"\t\tSubject: {relation[0]} ; Object: {relation[2]} ;")

                    if tuple(relation) not in results:
                        results.add(tuple(relation))
                        print("\t\tAdding to set of extracted relations\n")
                    else:
                        print("\t\tDuplicate. Ignoring this.\n")
                
        else:
            print("Parsed output is not a list:", parsed_relations)
            return num_extracted_tuples, num_extracted_sentences
    except json.JSONDecodeError as e:
        print("Error parsing JSON:", e)
        print("cleaned_text:", cleaned_text)
        return num_extracted_tuples, num_extracted_sentences
    
    return num_extracted_tuples, num_extracted_sentences