import argparse

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


def main():
    # Parse all user input from args
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

    # Map relation numbers to names for clarity
    relation_map = {
        1: "Schools_Attended",
        2: "Work_For",
        3: "Live_In",
        4: "Top_Member_Employees"
    }

    google_search_api_key = args.google_search_api_key
    google_engine_id = args.google_engine_id
    google_gemini_api_key = args.google_gemini_api_key
    extraction_method = args.extraction_method
    r = args.r
    t = args.t
    q = args.q 
    k = args.k

    # NOTE: we can delete this later I'm just making sure we parsed the args correctly
    print("Parsed Arguments:")
    print(f"Google Search API Key: {google_search_api_key}")
    print(f"Google Engine ID: {google_engine_id}")
    print(f"Google Gemini API Key: {google_gemini_api_key}")
    print(f"Extraction Method: {extraction_method}")
    print(f"Relation: {r} ({relation_map[r]})")
    print(f"Threshold: {t}")
    print(f"Seed Query: {q}")
    print(f"Number of Tuples: {k}")


if __name__ == '__main__':
    main()