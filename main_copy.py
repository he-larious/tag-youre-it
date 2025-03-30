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

entities_of_interest = ["ORGANIZATION", "PERSON", "LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]
relation_requirements = {
        "Schools_Attended": {"subj": "PERSON", "obj": ["ORGANIZATION"]},
        "Work_For": {"subj": "PERSON", "obj": ["ORGANIZATION"]},
        "Live_In": {"subj": "PERSON", "obj": ["LOCATION", "CITY", "STATE_OR_PROVINCE", "COUNTRY"]},
        "Top_Member_Employees": {"subj": "ORGANIZATION", "obj": ["PERSON"]}
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
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except Exception as e:
        # print(f"Skipping URL {url} due to retrieval error: {e}")
        print(e)
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

# Extract relations based on doc and 1) check for right pair of entity types 2) extract 3) check for duplicates based on results
# NOTE: expecting set() result type for gemini, expecting {} result type for spanBERT
def extract_relations(args, results, doc, requirement):
    num_processed = 0
    num_valid_sent = 0
    total_extracted = 0
    TOTAL = len(list(doc.sents))

    for sentence in doc.sents:

        # Create entity pairs
        candidate_pairs = []
        sentence_entity_pairs = create_entity_pairs(sentence, entities_of_interest)

        for ep in sentence_entity_pairs:
            # Get possible ordering of pairs
            pair1 = {"tokens": ep[0], "subj": ep[1], "obj": ep[2]}  # e1=Subject, e2=Object
            pair2 = {"tokens": ep[0], "subj": ep[2], "obj": ep[1]}  # e1=Object, e2=Subject

            # Keep subject-object pairs of the right type for the target relation
            if pair1["subj"][1] == requirement["subj"] and pair1["obj"][1] in requirement["obj"]:
                candidate_pairs.append(pair1)
            if pair2["subj"][1] == requirement["subj"] and pair2["obj"][1] in requirement["obj"]:
                candidate_pairs.append(pair2)
        
        if len(candidate_pairs) > 0:
            num_valid_sent += 1
            
            # TODO: Each method returns
            # 1) updated results (in a list or dictionary)
            # 2) updated count of total extractions (including the duplicates)
            if args.extraction_method == 'spanbert':
                results, total_extracted = [], 0
            else:
                results, total_extracted = [], 0
                # results, total_extracted = extract_relations_gemini(args.google_gemini_api_key, relation_map[args.r], sentence, results) #NOTE: only feeding gemini a sentence
        
        num_processed += 1
        if (num_processed % 5 == 0):
            print(f"Processed {num_processed} / {TOTAL} sentences")

    print(f"\tExtracted annotations for  {num_valid_sent}  out of total  {TOTAL}  sentences")
    print(f"\tRelations extracted from this website: {len(results)} (Overall: {total_extracted})")
    return results

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
    
    # Set up for iterations
    service = build("customsearch", "v1", developerKey=args.google_search_api_key)
    num_iteration = 0
    q = args.q
    nlp = spacy.load("en_core_web_lg")  # Load spacy model
    requirement = relation_requirements[relation_map[args.r]]

    while True:
        processed_queries.add(q)
        print(f"=========== Iteration: {num_iteration} - Query: {q} ===========\n\n")
        num_iteration += 1

        # Process query
        top_urls = process_query(q, service, args.google_engine_id)
        # url = top_urls[4]
        # print(requests.get(url, timeout=10))
        # # print(requests.get(url.strip(), timeout=10))
        # # print(type(url))
        # print(url)
        # # print(requests.get(str(url), timeout=10))
        # # print(requests.get(url.strip(), timeout=10).text)
        # # print(top_urls[1])
        # # print(top_urls)
        # url = "https://x.com/billgates"
        # print(requests.get(url, timeout=10))
        # print(requests.get(url.strip(), timeout=10).text)
        # print(requests.get("http://www.microsoft.com", timeout=10))
        # break
        # Process each url
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
            if text == None:
                print("Unable to fetch URL. Continuing.")
                continue

            print(f"\tWebpage length (num characters): {len(text)}")
            print("\tAnnotating the webpage using spacy...")
            # Process the text with spaCy (includes tokenization, sentence segmentation, and NER)
            doc = nlp(text)
            print(f"\tExtracted {len(list(doc.sents))} sentences. Processing each sentence one by one to check for presence of right pair of named entity types; if so, will run the second pipeline ...")

            # Extract relations
            results = extract_relations(args, results, doc, requirement)

        updated = False
        if args.extraction_method == 'gemini':
            relation = relation_map[args.r]
            print(f"================== ALL RELATIONS for {relation} ( {len(results)} ) =================")
            for res in results: # res = (subj, relation_type, obj)
                print(f"Subject: {res[0]}\t\t| Object: {res[2]}")
                if f"{res[0]} {res[2]}" not in processed_queries:
                    q = f"{res[0]} {res[2]}" # update q just in case
                    updated = True
        else:
            #TODO: update this to print table based on a dict
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