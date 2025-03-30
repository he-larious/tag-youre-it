import argparse
import re
from bs4 import BeautifulSoup
import requests
import spacy
from spacy_help_functions import get_entities, create_entity_pairs
from gemini import extract_relations_gemini
from googleapiclient.discovery import build

# Map relation numbers to names for clarity
relation_map = {
    1: "Schools_Attended",
    2: "Work_For",
    3: "Live_In",
    4: "Top_Member_Employees"
}
internal_map = {
    1: "per:schools_attended",
    2:"per:employee_of",
    3:"per:cities_of_residence",
    4:"org:top_members/employees"
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

    parser.add_argument("google_search_api_key", type=str, help="Google Custom Search Engine JSON API Key")
    parser.add_argument("google_engine_id", type=str, help="Google Engine ID")
    parser.add_argument("google_gemini_api_key", type=str, help="Google Gemini API Key")

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
        # print(f"Skipping URL {url} due to retrieval error: {e}")
        print(e)
        print("Unable to fetch URL. Continuing.")
        return None

    # Parse the HTML file
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove common unwanted tags
    for tag in soup.find_all(["script", "style", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # Extract plain text from the HTML
    raw_text = soup.get_text(separator=" ", strip=True)

    # Replace multiple whitespace characters (including newlines) with a single space
    raw_text = re.sub(r'\s+', ' ', raw_text).strip()

    # Truncate text if it's longer than max_length characters
    if len(raw_text) > max_length:
        print(f"\tTrimming webpage content from {len(raw_text)} to 10000 characters")
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

    # Each element will be a tuple with element 1 being the sentence and element 2 being the candidate pairs
    sentence_candidate_pairs = []

    # Iterate over each sentence and extract named entities
    
    print(f"\tExtracted {len(list(doc.sents))} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ...")
    num_sentences = 0

    for sentence in doc.sents:
        num_sentences += 1
        # print("\n\nProcessing sentence: {}".format(sentence))
        # print("Tokenized sentence: {}".format([token.text for token in sentence]))

        ents = get_entities(sentence, entities_of_interest)
        # print("spaCy extracted entities: {}".format(ents))

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
        
        if len(candidate_pairs) > 0:
            sentence_candidate_pairs.append((sentence, candidate_pairs))
    
    print("\tProcessed each sentence to only keep sentences where each entity pair contains both required named entities for the relation of interest.")
    print(f"\tWent from {num_sentences} total sentences to {len(sentence_candidate_pairs)} valid sentences.")

    return sentence_candidate_pairs




def extract_relations(args, sentence_candidate_pairs, results):
    #TODO both methods need to print to terminal throughout and end of process
    #TODO: return a list of tuples (if gemini --> (subj, obj). if spanbert --> (confidence, subj, obj))
    if args.extraction_method == 'spanbert':
        return [(1.0,"","")]
        # Call some helper function
        candidate_pairs = sentence_candidate_pairs[-1]
        
    
    elif args.extraction_method == 'gemini':
        # Get plain text sentences to feed into gemini
        sentences = []
        gemini_results = set()

        for sentence, candidate_pairs in sentence_candidate_pairs:
            sentences.append(sentence)

        extract_relations_gemini(args.google_gemini_api_key, relation_map[args.r], sentences, gemini_results)
        return list(gemini_results)

def process_query(q, service, engine_id):
    """
    This function processes a search query by calling the Google Custom Search Engine API
    and returns a list of search results containing the title, URL, and description.

    Parameters:
        q (str): The search query string to be submitted to the search engine.
        service (object): An authenticated Google API client service object for interacting with the API.

    Returns:
        list: A 2D list where each element is a list in the form [title, url, description].
    """
    res = (
        service.cse()
        .list(
            q=q,
            cx=engine_id,
        )
        .execute()
    )
    results = [item["link"] for item in res["items"]]
    # for item in res["items"]:
    #     title = item["title"]
    #     url = item["link"]
    #     description = item["snippet"]

    #     results.append([title, url, description])

    return results


def main():
    # Parse and validate all user input from args
    args = validate_args()

    # Print to intro to terminal
    print("____")
    print("Parameters:")
    print(f"Client key	= {args.google_search_api_key}")
    print(f"Engine key	= {args.google_engine_id}")
    print(f"Gemini key	= {args.google_gemini_api_key}")
    print(f"Method	= {args.extraction_method}")
    print(f"Relation	= {relation_map[args.r]}")
    print(f"Threshold	= {args.t}")
    print(f"Query		= {args.q}")
    print(f"# of Tuples	= {args.k}")
    print("Loading necessary libraries; This should take a minute or so ...)")

    # Keep track of URLs that have been processed in previous urls, queries, results
    processed_urls = set()
    processed_queries = set()
    gemini_res = set()
    spanbert_res = {}
    if args.extraction_method == 'spanbert':
        results = spanbert_res
    else:
        results = gemini_res 
    
    # Start iterations
    service = build("customsearch", "v1", developerKey=args.google_search_api_key)
    num_iteration = 0
    q = args.q
    while True:
        processed_queries.add(q)
        print(f"=========== Iteration: {num_iteration} - Query: {q} ===========\n\n")
        num_iteration += 1

        # Process query
        top_urls = process_query(q, service, args.google_engine_id)

        # process each url
        count = 0
        while(count < 10):
            curr_url = top_urls[count]
            print(f"URL ( {count+1} / 10): {curr_url}")
            count += 1
            if curr_url in processed_urls:
                print("This URL has already been processed. Continuing.")
                continue
            processed_urls.add(curr_url)
            print("\tFetching text from url ...")
            text = extract_plain_text(curr_url)
            if text == None: # unable to retrieve page
                continue
            print(f"\tWebpage length (num characters): {len(text)}")
            print("\tAnnotating the webpage using spacy...")
            sentence_candidate_pairs = extract_named_entities(text, args)
            results = extract_relations(args, sentence_candidate_pairs, results)

        updated = False
        if args.extraction_method == 'gemini':
            relation = relation_map[args.r]
            print(f"================== ALL RELATIONS for {relation} ( {len(results)} ) =================")
            for res in results: # res = (subj,obj)
                print(f"Subject: {res[0]}\t\t| Object: {res[1]}")
                if f"{res[0]} {res[1]}" not in processed_queries:
                    q = f"{res[0]} {res[1]}" # update q just in case
                    updated = True
        else:
            relation = internal_map[args.r]
            print(f"================== ALL RELATIONS for {relation} ( {len(results)} ) =================")
            for res in results: # res = (confidence,subj,obj)
                print(f" Confidence: {res[0]}\t\t| Subject: {res[1]}\t\t| Object: {res[2]}")
                if f"{res[1]} {res[2]}" not in processed_queries:
                    q = f"{res[1]} {res[2]}" # update q just in case
                    updated = True

        # if we reached k tuples
        if len(results) >= args.k:
            print(f"Total # of iterations = {num_iteration+1}")
            break
        
        # if there was no q
        if not updated:
            print("ISE has 'stalled' before retrieving k high-confidence tuples")
            break


if __name__ == '__main__':
    main()