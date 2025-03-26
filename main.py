import argparse
from bs4 import BeautifulSoup
import requests
# import spacy
# from spacy_help_functions import get_entities, create_entity_pairs
from gemini import extract_relations_gemini

# Map relation numbers to names for clarity
relation_map = {
    1: "Schools_Attended",
    2: "Work_For",
    3: "Live_In",
    4: "Top_Member_Employees"
}


def check_threshold(value):
    """
    Check that the user inputted argument for the extraction confidence threshold
    is a float between 0 and 1.
    """
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Threshold must be a float.")
    if f < 0 or f > 1:
        raise argparse.ArgumentTypeError("Threshold must be between 0 and 1.")
    return f


def check_positive_int(value):
    """
    Check that the user inputted argument for the number of tuples to extract
    is an integer greater than 0.
    """
    try:
        i = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Value must be an integer.")
    if i <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than 0.")
    return i


def validate_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("google_search_api_key", type=str, help="Google Custom Search Engine JSON API Key")
    parser.add_argument("google_engine_id", type=str, help="Google Engine ID")
    parser.add_argument("google_gemini_api_key", type=str, help="Google Gemini API Key")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-spanbert",
        dest="extraction_method",
        action="store_const",
        const="spanbert",
        help="Use SpanBERT for information extraction"
    )
    group.add_argument(
        "-gemini",
        dest="extraction_method",
        action="store_const",
        const="gemini",
        help="Use Google Gemini for information extraction"
    )

    parser.add_argument(
        "r", 
        type=int,
        choices=range(1, 5),
        help=("Relation to extract: 1 = Schools_Attended, 2 = Work_For, 3 = Live_In, 4 = Top_Member_Employees")
    )
    parser.add_argument("t", type=check_threshold, help="Extraction confidence threshold between 0 and 1 (ignored for Gemini)")
    parser.add_argument("q", type=str, help='Seed query as a quoted string, ex. "bill gates microsoft"')
    parser.add_argument("k", type=check_positive_int, help="Number of tuples to request (must be > 0)")

    args = parser.parse_args()
    return args


def extract_plain_text(url, max_length=10000):
    """
    Retrieve the webpage. Skip if there's an error. Extract plain text using BeautifulSoup.
    Truncate text to max_length if necessary.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 
    except Exception as e:
        print(f"Skipping URL {url} due to retrieval error: {e}")
        return None

    # Parse the HTML file
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove unwanted tags (<script> and <style>)
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Extract plain text from the HTML
    raw_text = soup.get_text(separator=" ", strip=True)

    # Truncate text if it's longer than max_length characters
    if len(raw_text) > max_length:
        raw_text = raw_text[:max_length]

    return raw_text


def extract_named_entities(raw_text, args):
    entities_of_interest = ["ORGANIZATION", "PERSON", "LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]
    relation_requirements = {
        "Schools_Attended": {"subj": "PERSON", "obj": ["ORGANIZATION"]},
        "Work_For": {"subj": "PERSON", "obj": ["ORGANIZATION"]},
        "Live_In": {"subj": "PERSON", "obj": ["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]},
        "Top_Member_Employees": {"subj": "ORGANIZATION", "obj": ["PERSON"]}
    }

    requirement = relation_requirements[relation_map[args.r]]

    # Load spacy model
    nlp = spacy.load("en_core_web_lg")

    # Process the text with spaCy (includes tokenization, sentence segmentation, and NER)
    doc = nlp(raw_text)

    # Iterate over each sentence and extract named entities
    for sentence in doc.sents:
        print("\n\nProcessing sentence: {}".format(sentence))
        print("Tokenized sentence: {}".format([token.text for token in sentence]))

        ents = get_entities(sentence, entities_of_interest)
        print("spaCy extracted entities: {}".format(ents))

        # Create entity pairs
        candidate_pairs = []
        sentence_entity_pairs = create_entity_pairs(sentence, entities_of_interest)

        for ep in sentence_entity_pairs:
            # Keep subject-object pairs of the right type for the target relation 
            pair1 = {"tokens": ep[0], "subj": ep[1], "obj": ep[2]}  # e1=Subject, e2=Object
            pair2 = {"tokens": ep[0], "subj": ep[2], "obj": ep[1]}  # e1=Object, e2=Subject

            if pair1["subj"][1] == requirement["subj"] and pair1["obj"][1] in requirement["obj"]:
                candidate_pairs.append(pair1)
            if pair2["subj"][1] == requirement["subj"] and pair2["obj"][1] in requirement["obj"]:
                candidate_pairs.append(pair2)
    
    return candidate_pairs


def extract_relations(args, text):
    if args.method == 'spanbert':
        # Call some helper function
        pass
    elif args.method == 'gemini':
        extract_relations_gemini(args.google_gemini_api_key)


def main():
    # Parse and validate all user input from args
    args = validate_args()

    # Print to terminal
    print("Parameters:")
    print(f"Google Search API Key: {args.google_search_api_key}")
    print(f"Google Engine ID: {args.google_engine_id}")
    print(f"Google Gemini API Key: {args.google_gemini_api_key}")
    print(f"Extraction Method: {args.extraction_method}")
    print(f"Relation: {args.r} ({relation_map[args.r]})")
    print(f"Threshold: {args.t}")
    print(f"Seed Query: {args.q}")
    print(f"Number of Tuples: {args.k}")

    # NOTE: Testing things for now, can delete later
    text = extract_plain_text('http://infolab.stanford.edu/~sergey/')
    print(text)
    candidate_pairs = extract_named_entities(text)
    print(candidate_pairs)

    # Keep track of URLs that have been processed in previous iterations
    processed_urls = set()


if __name__ == '__main__':
    main()