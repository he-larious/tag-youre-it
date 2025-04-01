# tag-youre-it
COMS 6111 Project 2

## Group
Helena He (hh3090) <br>
Kristine Pham (klp2157)

## Files
- main.py
- gemini.py
- spanbert_process.py
- requirements.txt
- transcript_gemini.txt
- transcript_spanbert.txt
- README.md

## To Run the Program:
To install all packages needed to run the program, use this command:
```
pip install -r requirements.txt
```

To run the program, use this command:
```
python3 main.py [-spanbert|-gemini] <google api key> <google engine id> <google gemini api key> <r> <t> <q> <k>
```

## Project Design

### Code Structure
1. The user inputs
    - extraction method,
    - relevant google api keys,
    - google engine ID,
    - a target relation,
    - desired threshold,
    - search query
    - and a target minimum number of tuples to return.
2. The query is sent to the Google Custom Search API. The ```process_query()``` function interacts with the API to retrieve the top 10 urls.
3. For each url that has not been processed before,
    - The function ```extract_plain_text()``` retrieves the plain text of the webpage
    - The function ```nlp()``` applies spacy model to raw text (to split to sentences, tokenize, extract entities etc.)
    - The function ```extract_relations()``` extracts unique target relations (and replaces duplicate with higher thresholds if spanBERT) and add them to results.
4. A table of current results is printed.
5. If we haven't reach the target minimum number of tuples to return, we will use a new tuple from results to query another round of urls.
6. This process is repeated until the desired number of tuples is reached or there are no more new queries options from results.

### Externel Libraries
1. **argparse** - used to defines required command line inputs (like API keys, relation type, threshold, etc.) and checks that certain inputs (such as the confidence threshold and the number of tuples) are within valid ranges.
2. **re** - used to clean up the extracted text by removing redundant whitespace after HTML parsing.
3. **BeautifulSoup** - used to extract plain text from a fetched HTML webpage by stripping out unwanted tags (such as script, style, etc.)
4. **requests** - used to retrieve webpages based on URLs provided by the Google Custom Search API.
5. **spacy** - used to load a pre-trained language model for tasks such as tokenization, sentence segmentation, and named entity recognition.
6. **googleapiclient.discovery** - used to interact with the Google Custom Search API by performing search queries and retrieving relevant URLs.
7. **google.generativeai** - used to interact with Google’s Gemini model by sending prompts and receiving generated responses.

## Step 3 Description
For each unprocessed URL, we start by calling the `extract_plain_text()` function. It will:

1. Send an HTTP GET request with a timeout of 10 seconds to fetch the webpage.
2. Once the webpage is successfully retrieved, use BeautifulSoup to parse the HTML and remove unnecessary elements such as scripts, styles, headers, footers, navigation, and aside tags.
3. Extract the plain text from the HTML, replace tabs and newlines with spaces, and reduce multiple spaces to a single space.
4. Finally, if the resulting text exceeds the maximum length (10,000 characters), truncate it accordingly and returns the final plain text.

Next, the `extract_relations()` function is called. It will:

1. Iterate over every sentence in the document and generate candidate entity pairs using a helper function called `create_entity_pairs()`. 
2. For each entity pair, create two possible orderings. The first ordering will have the first entity as the subject and the second entity as the object. The second ordering will have the first entity as the object and the second entity as the subject.
3. Filter these candidate pairs to only include those that match the specified target relation requirement for the subject and object types. 
4. If any valid candidate pairs are found, extract relations using one of two extraction methods: SpanBERT or Gemini.

For SpanBERT, a function called `extract_relations_spanbert()` is called. It will:

1. Run SpanBERT on the given list of candidate entity pairs to predict relations and their confidences
2. For each relation prediction that matches the target relation, we will add it to the dictionary of results if 1) it is equal to or above the desired threshold and if 2) it has a higher threshold than its exact duplicated in the results. We will implicitly remove the duplicate that has the lower threshold.
3. At the end, we sort the result dictionary so that it is in descending order.

For Gemini, a function called `extract_relations_gemini()` is called. It will:

1. Configure the generative AI library with the provided API key. 
2. Construct a prompt using one-shot learning that includes an example output, an example sentence, and instructions for extracting instances of the target relation. The output should be a list of lists, where each inner array is formatted as ["Subject: {subj_type}", "{relation}", "Object: {obj_type}"].
3. Call the `get_gemini_completion()` helper function with the constructed prompt to generate a response from Gemini for the prompt.
4. If the request fails, use an exponential backoff retry mechanism with a maximum of five retries and added random jitter to avoid resource exhaustion. 
5. Once a successful response is obtained (or the retries are exhausted), parse the response using the `parse_response_text()` helper function. 
6. Add all parsed relations to the results set.
7. Add a short pause before returning to ensure that the extraction process does not overload the API.

## Google Custom Search Engine
API Key - AIzaSyDoyk2WXtfi8eu5kYEKhEV4J8WlgPpBTfs <br>
Engine ID - a6b6d898d001649c2